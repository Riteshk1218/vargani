import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../api/api_client.dart';
import '../state/app_state.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'followups_screen.dart';
import 'people_screen.dart';
import 'receipt_screen.dart';

const collectionModes = ['cash', 'upi', 'bank_transfer', 'cheque', 'other'];
const modesNeedingReference = {'upi', 'bank_transfer', 'cheque'};

class _Line {
  String? typeId;
  final amount = TextEditingController();
  String? month; // YYYY-MM-01
}

/// "500.00" -> 50000 paise, so amounts can be compared without floating point.
int _paise(String? amount) {
  if (amount == null) return 0;
  final parts = amount.split('.');
  return int.parse(parts[0]) * 100 + (parts.length > 1 ? int.parse(parts[1].padRight(2, '0').substring(0, 2)) : 0);
}

String _fromPaise(int paise) => '${paise ~/ 100}.${(paise % 100).toString().padLeft(2, '0')}';

/// Karyakarta workflow: who paid (optional) → type → amount → month → mode → save → receipt.
///
/// Who paid can be an existing person, a new person typed in here (saved for next time), or nobody
/// named: an anonymous collection still gets a receipt. Date and time are recorded by the server.
class CollectScreen extends StatefulWidget {
  const CollectScreen({super.key, this.person});
  final Map<String, dynamic>? person;

  @override
  State<CollectScreen> createState() => _CollectScreenState();
}

class _CollectScreenState extends State<CollectScreen> {
  // One key per screen visit: a retried Save after a dropped connection returns the
  // first payment instead of recording it twice.
  String _idempotencyKey = const Uuid().v4();
  Map<String, dynamic>? _person;
  String _payerKind = 'existing'; // existing | new | anonymous
  final _newName = TextEditingController();
  final _newMobile = TextEditingController();
  List<Map<String, dynamic>>? _types;
  Object? _loadError;
  final List<_Line> _lines = [_Line()];
  String _mode = 'cash';
  // Answers to the organization's own dropdowns (admin studio): field key -> option.
  final Map<String, String> _custom = {};
  final _reference = TextEditingController();
  final _notes = TextEditingController();
  // Money that came now; empty means all of it. The rest is kept as a balance for the person.
  final _received = TextEditingController();
  List<Map<String, dynamic>> _dues = const [];
  // When to go back to this house for the balance (YYYY-MM-DD).
  String? _followUp = () {
    final d = DateTime.now().add(const Duration(days: 1));
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }();
  String? _opening; // pavti being opened for an update
  bool _saving = false;
  ApiException? _error;

  @override
  void initState() {
    super.initState();
    _person = widget.person;
    final modes = _modes(AppScope.read(context));
    if (modes.isNotEmpty && !modes.contains(_mode)) _mode = modes.first;
    _loadTypes();
    _loadDues();
  }

  /// Balances this person still owes in this event, so the collector can update that pavti.
  Future<void> _loadDues() async {
    final app = AppScope.read(context);
    final id = _person?['id'];
    if (id == null) {
      setState(() => _dues = const []);
      return;
    }
    try {
      final data = await app.api.get('/dues/', query: {'event': app.eventId, 'person': '$id', 'open': 'true'});
      if (mounted) setState(() => _dues = resultsOf(data));
    } catch (_) {
      if (mounted) setState(() => _dues = const []);
    }
  }

  /// Open balances grouped by pavti: payment id -> (receipt number, still owed in paise).
  Map<String, ({String? receipt, int paise})> get _owedPavtis {
    final out = <String, ({String? receipt, int paise})>{};
    for (final d in _dues) {
      final id = '${d['payment']}';
      final before = out[id];
      out[id] = (receipt: d['receipt_number']?.toString(), paise: (before?.paise ?? 0) + _paise('${d['remaining']}'));
    }
    return out;
  }

  /// Opens an earlier pavti of this person to add money or move its follow-up date. No new pavti is made.
  Future<void> _updatePavti(String paymentId) async {
    final app = AppScope.read(context);
    setState(() => _opening = paymentId);
    try {
      final payment = await app.api.get('/payments/$paymentId/');
      if (!mounted) return;
      final saved = await Navigator.push<bool>(
        context,
        MaterialPageRoute(builder: (_) => PavtiVisitScreen(payment: payment as Map)),
      );
      if (saved == true) _loadDues();
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  /// Modes the admin studio still shows.
  List<String> _modes(AppState app) => [
    for (final m in collectionModes)
      if (!app.modeHidden(m)) m,
  ];

  bool get _named => (_payerKind == 'existing' && _person != null) || _payerKind == 'new';

  int get _totalPaise => _lines.fold(0, (sum, l) => sum + _paise(normaliseAmount(l.amount.text)));

  /// What is not received now is kept as a balance on the pavti.
  int _balancePaise(int received) => received < _totalPaise ? _totalPaise - received : 0;

  /// The received amount typed in, in paise, or null when it was left empty (all of it came).
  int? get _receivedPaise {
    final raw = _received.text.trim();
    if (raw.isEmpty || !_named) return null;
    if (RegExp(r'^0+(\.0{1,2})?$').hasMatch(raw)) return 0;
    final v = normaliseAmount(raw);
    return v == null ? -1 : _paise(v);
  }

  Future<void> _loadTypes() async {
    final app = AppScope.read(context);
    try {
      final data = await app.api.get('/contribution-types/', query: {'event': app.eventId, 'is_active': 'true'});
      final types = resultsOf(data);
      setState(() {
        _types = types;
        _loadError = null;
        // Lines start on the first type in the event's order: Donation, for the default types.
        for (final line in _lines) {
          line.typeId ??= types.firstOrNull?['id'] as String?;
        }
      });
    } catch (e) {
      setState(() => _loadError = e);
    }
  }

  Map<String, dynamic>? _type(String? id) => _types?.where((t) => t['id'] == id).firstOrNull;

  List<DateTime> _months() {
    final app = AppScope.read(context);
    final now = DateTime.now();
    DateTime? parse(Object? s) => s == null ? null : DateTime.tryParse('$s');
    var start = parse(app.event?['start_date']) ?? DateTime(now.year, now.month - 11);
    var end = parse(app.event?['end_date']) ?? now;
    if (end.isAfter(DateTime(now.year, now.month + 1))) end = DateTime(now.year, now.month);
    final out = <DateTime>[];
    var d = DateTime(start.year, start.month);
    while (!d.isAfter(end) && out.length < 36) {
      out.add(d);
      d = DateTime(d.year, d.month + 1);
    }
    return out.reversed.toList();
  }

  String _monthValue(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-01';
  String _monthLabel(DateTime d) {
    const m = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return '${m[d.month - 1]} ${d.year}';
  }

  Future<void> _pickPerson() async {
    final p = await Navigator.push<Map<String, dynamic>>(
      context,
      MaterialPageRoute(
        builder: (ctx) => Scaffold(
          appBar: AppBar(title: Text(AppScope.of(ctx).t('select_person'))),
          body: PersonSearchList(searchFirst: true, onPick: (p) => Navigator.pop(ctx, p)),
        ),
      ),
    );
    if (p != null) {
      setState(() => _person = p);
      _loadDues();
    }
  }

  Future<void> _save() async {
    final app = AppScope.read(context);
    final t = app.t;
    if (_payerKind == 'new' && _newName.text.trim().isEmpty) {
      showMessage(context, t('enter_name'), error: true);
      return;
    }
    final lines = <Map<String, dynamic>>[];
    for (final l in _lines) {
      final amount = normaliseAmount(l.amount.text);
      if (l.typeId == null || amount == null) {
        setState(() {});
        showMessage(context, l.typeId == null ? t('choose_type') : t('invalid_amount'), error: true);
        return;
      }
      lines.add({
        'contribution_type': l.typeId,
        'amount': amount,
        if (_type(l.typeId)?['kind'] == 'recurring_monthly' && l.month != null) 'period_month': l.month,
      });
    }
    for (final f in app.customFields) {
      if (f['required'] == true && (_custom[f['key']] ?? '').isEmpty) {
        showMessage(context, t('fill_field', {'field': '${f['label']}'}), error: true);
        return;
      }
    }
    final received = _receivedPaise;
    if (received != null && (received < 0 || received > _totalPaise)) {
      showMessage(context, t('received_too_much'), error: true);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final payment = await app.api.post(
        '/collections/',
        {
          'event': app.eventId,
          'payer': _payerKind == 'existing' ? (_person?['id']) : null,
          if (_payerKind == 'new')
            'new_person': {
              'full_name': _newName.text.trim(),
              if (_newMobile.text.trim().isNotEmpty) 'mobile': _newMobile.text.trim(),
            },
          'mode': _mode,
          'reference_number': _reference.text.trim(),
          'notes': _notes.text.trim(),
          'lines': lines,
          'custom_fields': {
            for (final f in app.customFields)
              if ((_custom[f['key']] ?? '').isNotEmpty) '${f['key']}': _custom[f['key']],
          },
          if (received != null && received < _totalPaise) 'received': _fromPaise(received),
          if (received != null && received < _totalPaise) 'follow_up_on': _followUp,
        },
        {'Idempotency-Key': _idempotencyKey},
      );
      _idempotencyKey = const Uuid().v4();
      final receipt = (payment as Map)['receipt'] as Map?;
      if (!mounted) return;
      if (receipt != null) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${receipt['id']}', justIssued: true)),
        );
      } else {
        showMessage(context, t('saved'));
        Navigator.pop(context);
      }
    } on ApiException catch (e) {
      setState(() => _error = e);
      showMessage(context, e.message, error: true);
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    return Scaffold(
      appBar: AppBar(title: Text(t('collect')), actions: const [EventSwitcher()]),
      body: _types == null
          ? Center(
              child: _loadError == null
                  ? const CircularProgressIndicator()
                  : Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(errorText(context, _loadError!)),
                        TextButton(onPressed: _loadTypes, child: Text(t('retry'))),
                      ],
                    ),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (widget.person == null) ...[
                  Text(
                    '${app.fieldLabel('payer', t('payer'))} (${t('optional')})',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 8),
                  SegmentedButton<String>(
                    key: const Key('payer-kind'),
                    showSelectedIcon: false,
                    segments: [
                      ButtonSegment(
                        value: 'existing',
                        icon: const Icon(Icons.person_search),
                        label: Text(t('payer_existing')),
                      ),
                      if (app.can('people.create') || app.can('people.manage'))
                        ButtonSegment(
                          value: 'new',
                          icon: const Icon(Icons.person_add_alt),
                          label: Text(t('payer_new')),
                        ),
                      ButtonSegment(
                        value: 'anonymous',
                        icon: const Icon(Icons.person_off_outlined),
                        label: Text(t('payer_anonymous')),
                      ),
                    ],
                    selected: {_payerKind},
                    onSelectionChanged: (s) => setState(() => _payerKind = s.first),
                  ),
                  const SizedBox(height: 8),
                ],
                if (_payerKind == 'existing')
                  Card(
                    child: ListTile(
                      key: const Key('collect-person'),
                      leading: const Icon(Icons.person),
                      title: Text(_person?['full_name']?.toString() ?? t('select_person')),
                      subtitle: Text(
                        _error?.fieldError('payer') ??
                            (_person == null ? t('no_person_anonymous') : '${_person?['mobile'] ?? t('payer')}'),
                        style: _error?.fieldError('payer') != null
                            ? TextStyle(color: Theme.of(context).colorScheme.error)
                            : null,
                      ),
                      trailing: widget.person == null ? const Icon(Icons.edit) : null,
                      onTap: widget.person == null ? _pickPerson : null,
                    ),
                  ),
                if (_payerKind == 'new')
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        children: [
                          TextField(
                            key: const Key('new-person-name'),
                            controller: _newName,
                            textCapitalization: TextCapitalization.words,
                            decoration: InputDecoration(
                              labelText: t('full_name'),
                              errorText: _error?.fieldError('new_person.full_name'),
                              border: const OutlineInputBorder(),
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            key: const Key('new-person-mobile'),
                            controller: _newMobile,
                            keyboardType: TextInputType.phone,
                            decoration: InputDecoration(
                              labelText: '${t('mobile')} (${t('optional')})',
                              errorText: _error?.fieldError('new_person.mobile'),
                              border: const OutlineInputBorder(),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(t('new_person_saved'), style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ),
                    ),
                  ),
                if (_payerKind == 'anonymous')
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.person_off_outlined),
                      title: Text(t('anonymous')),
                      subtitle: Text(t('anonymous_note')),
                    ),
                  ),
                if (_payerKind == 'existing' && _dues.isNotEmpty)
                  Card(
                    key: const Key('collect-dues'),
                    color: Colors.amber.shade50,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                          child: Text(
                            '${t('balance_due')}: ${formatInr(_fromPaise(_dues.fold(0, (sum, d) => sum + _paise('${d['remaining']}'))))}',
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
                          child: Text(t('same_pavti_hint'), style: Theme.of(context).textTheme.bodySmall),
                        ),
                        for (final e in _owedPavtis.entries)
                          ListTile(
                            dense: true,
                            title: Text(e.value.receipt ?? t('pavti')),
                            subtitle: Text('${formatInr(_fromPaise(e.value.paise))} ${t('still_owed')}'),
                            trailing: FilledButton.tonal(
                              key: Key('update-pavti-${e.key}'),
                              onPressed: _opening == null ? () => _updatePavti(e.key) : null,
                              child: _opening == e.key
                                  ? const SizedBox(
                                      height: 16,
                                      width: 16,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : Text(t('update_pavti')),
                            ),
                          ),
                      ],
                    ),
                  ),
                const SizedBox(height: 8),
                for (var i = 0; i < _lines.length; i++) _lineCard(i),
                if (_types!.length > 1)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      icon: const Icon(Icons.add),
                      label: Text(t('add_line')),
                      onPressed: () => setState(() => _lines.add(_Line()..typeId = _types!.first['id'] as String)),
                    ),
                  ),
                if (_named) ...[
                  const SizedBox(height: 8),
                  TextField(
                    key: const Key('collect-received'),
                    controller: _received,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      labelText: app.fieldLabel('received', t('received_now')),
                      prefixText: '₹ ',
                      hintText: _fromPaise(_totalPaise),
                      helperText: t('received_hint'),
                      helperMaxLines: 3,
                      errorText: _error?.fieldError('received'),
                      border: const OutlineInputBorder(),
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  if ((_receivedPaise ?? -1) >= 0 && _balancePaise(_receivedPaise!) > 0) ...[
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        '${t('balance_due')}: ${formatInr(_fromPaise(_balancePaise(_receivedPaise!)))}',
                        key: const Key('collect-balance'),
                        style: TextStyle(color: Colors.amber.shade900, fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(height: 12),
                    FollowUpDateField(
                      key: const Key('collect-follow-up'),
                      value: _followUp,
                      error: _error?.fieldError('follow_up_on'),
                      onChanged: (v) => setState(() => _followUp = v),
                    ),
                  ],
                ],
                const SizedBox(height: 8),
                Text(app.fieldLabel('mode', t('payment_mode')), style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final m in _modes(app))
                      ChoiceChip(
                        key: Key('mode-$m'),
                        label: Text(modeLabel(app, m)),
                        selected: _mode == m,
                        onSelected: (_) => setState(() => _mode = m),
                      ),
                  ],
                ),
                if (_error?.fieldError('mode') != null)
                  Text(_error!.fieldError('mode')!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                const SizedBox(height: 16),
                if (modesNeedingReference.contains(_mode) || _reference.text.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: TextField(
                      key: const Key('collect-reference'),
                      controller: _reference,
                      decoration: InputDecoration(
                        labelText: app.fieldLabel(_mode == 'cheque' ? 'cheque_number' : 'reference', t('reference')),
                        helperText: t('reference_required'),
                        errorText: _error?.fieldError('reference_number'),
                        border: const OutlineInputBorder(),
                      ),
                    ),
                  ),
                for (final f in app.customFields)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: DropdownButtonFormField<String>(
                      key: Key('collect-custom-${f['key']}'),
                      initialValue: _custom[f['key']],
                      isExpanded: true,
                      decoration: InputDecoration(
                        labelText: f['required'] == true ? '${f['label']} *' : '${f['label']} (${t('optional')})',
                        errorText: _error?.fieldError('custom_fields.${f['key']}'),
                        border: const OutlineInputBorder(),
                      ),
                      hint: Text(t('choose')),
                      items: [
                        for (final o in (f['options'] as List? ?? const []))
                          DropdownMenuItem(
                            value: '$o',
                            child: Text('$o', overflow: TextOverflow.ellipsis),
                          ),
                      ],
                      onChanged: (v) => setState(() => _custom['${f['key']}'] = v ?? ''),
                    ),
                  ),
                TextField(
                  controller: _notes,
                  maxLength: 500,
                  decoration: InputDecoration(
                    labelText: app.fieldLabel('notes', t('notes')),
                    border: const OutlineInputBorder(),
                  ),
                ),
                Text(t('time_auto'), style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 8),
                FilledButton.icon(
                  key: const Key('collect-save'),
                  onPressed: _saving ? null : _save,
                  icon: _saving
                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.check),
                  label: Padding(padding: const EdgeInsets.all(12), child: Text(t('save_payment'))),
                ),
              ],
            ),
    );
  }

  Widget _lineCard(int i) {
    final app = AppScope.of(context);
    final t = app.t;
    final line = _lines[i];
    final type = _type(line.typeId);
    final min = type?['suggested_min'], max = type?['suggested_max'];
    String? hint;
    if (min != null && max != null && min != max) {
      hint = t('suggested', {'range': '${formatInr('$min')}–${formatInr('$max')}'});
    } else if (min != null || max != null) {
      hint = t('suggested', {'range': formatInr('${min ?? max}')});
    }
    final monthly = type?['kind'] == 'recurring_monthly';
    final months = monthly ? _months() : const <DateTime>[];
    if (monthly && line.month == null && months.isNotEmpty) {
      final now = DateTime.now();
      line.month = _monthValue(
        months.firstWhere((m) => m.year == now.year && m.month == now.month, orElse: () => months.first),
      );
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            DropdownButtonFormField<String>(
              key: Key('collect-type-$i'),
              initialValue: line.typeId,
              isExpanded: true,
              decoration: InputDecoration(
                labelText: app.fieldLabel('contribution_type', t('contribution_type')),
                errorText: _error?.fieldError('lines.$i.contribution_type'),
                border: const OutlineInputBorder(),
              ),
              items: [
                for (final ct in _types!)
                  DropdownMenuItem(
                    value: ct['id'] as String,
                    child: Text(
                      ct['fund_name'] != null ? '${ct['name']} · ${ct['fund_name']}' : '${ct['name']}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: (v) => setState(() {
                line.typeId = v;
                line.month = null;
              }),
            ),
            const SizedBox(height: 12),
            TextField(
              key: Key('collect-amount-$i'),
              controller: line.amount,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: app.fieldLabel('amount', t('amount')),
                prefixText: '₹ ',
                helperText: hint,
                errorText:
                    _error?.fieldError('lines.$i.amount') ??
                    (line.amount.text.isNotEmpty && normaliseAmount(line.amount.text) == null
                        ? t('invalid_amount')
                        : null),
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() {}),
            ),
            if (monthly) ...[
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: line.month,
                decoration: InputDecoration(
                  labelText: app.fieldLabel('month', t('month')),
                  errorText: _error?.fieldError('lines.$i.period_month'),
                  border: const OutlineInputBorder(),
                ),
                items: [for (final m in months) DropdownMenuItem(value: _monthValue(m), child: Text(_monthLabel(m)))],
                onChanged: (v) => setState(() => line.month = v),
              ),
            ],
            if (_lines.length > 1)
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(onPressed: () => setState(() => _lines.removeAt(i)), child: Text(t('remove'))),
              ),
          ],
        ),
      ),
    );
  }
}
