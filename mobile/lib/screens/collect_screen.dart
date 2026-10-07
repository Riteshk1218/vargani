import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'people_screen.dart';
import 'receipt_screen.dart';

const collectionModes = ['cash', 'upi', 'bank_transfer', 'cheque', 'other'];
const modesNeedingReference = {'upi', 'bank_transfer', 'cheque'};

class _Line {
  String? typeId;
  final amount = TextEditingController();
  String? month; // YYYY-MM-01
}

/// Karyakarta workflow: person → type → amount → month → mode → save → receipt.
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
  List<Map<String, dynamic>>? _types;
  Object? _loadError;
  final List<_Line> _lines = [_Line()];
  String _mode = 'cash';
  final _reference = TextEditingController();
  final _notes = TextEditingController();
  bool _saving = false;
  ApiException? _error;

  @override
  void initState() {
    super.initState();
    _person = widget.person;
    _loadTypes();
  }

  Future<void> _loadTypes() async {
    final app = AppScope.read(context);
    try {
      final data = await app.api.get('/contribution-types/', query: {'event': app.eventId, 'is_active': 'true'});
      final types = resultsOf(data);
      setState(() {
        _types = types;
        _loadError = null;
        if (types.length == 1) _lines.first.typeId = types.first['id'] as String;
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
          body: PersonSearchList(onPick: (p) => Navigator.pop(ctx, p)),
        ),
      ),
    );
    if (p != null) setState(() => _person = p);
  }

  Future<void> _save() async {
    final app = AppScope.read(context);
    final t = app.t;
    if (_person == null) {
      showMessage(context, t('select_person'), error: true);
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
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final payment = await app.api.post(
        '/collections/',
        {
          'event': app.eventId,
          'payer': _person!['id'],
          'mode': _mode,
          'reference_number': _reference.text.trim(),
          'notes': _notes.text.trim(),
          'lines': lines,
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
                  : Column(mainAxisSize: MainAxisSize.min, children: [
                      Text(errorText(context, _loadError!)),
                      TextButton(onPressed: _loadTypes, child: Text(t('retry'))),
                    ]),
            )
          : ListView(padding: const EdgeInsets.all(16), children: [
              Card(
                child: ListTile(
                  key: const Key('collect-person'),
                  leading: const Icon(Icons.person),
                  title: Text(_person?['full_name']?.toString() ?? t('select_person')),
                  subtitle: Text(_error?.fieldError('payer') ?? '${_person?['mobile'] ?? t('payer')}',
                      style: _error?.fieldError('payer') != null
                          ? TextStyle(color: Theme.of(context).colorScheme.error)
                          : null),
                  trailing: const Icon(Icons.edit),
                  onTap: widget.person == null ? _pickPerson : null,
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
                    onPressed: () => setState(() => _lines.add(_Line())),
                  ),
                ),
              const SizedBox(height: 8),
              Text(t('payment_mode'), style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final m in collectionModes)
                  ChoiceChip(
                    key: Key('mode-$m'),
                    label: Text(modeLabel(app, m)),
                    selected: _mode == m,
                    onSelected: (_) => setState(() => _mode = m),
                  ),
              ]),
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
                      labelText: t('reference'),
                      helperText: t('reference_required'),
                      errorText: _error?.fieldError('reference_number'),
                      border: const OutlineInputBorder(),
                    ),
                  ),
                ),
              TextField(
                controller: _notes,
                maxLength: 500,
                decoration: InputDecoration(labelText: t('notes'), border: const OutlineInputBorder()),
              ),
              const SizedBox(height: 8),
              FilledButton.icon(
                key: const Key('collect-save'),
                onPressed: _saving ? null : _save,
                icon: _saving
                    ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.check),
                label: Padding(padding: const EdgeInsets.all(12), child: Text(t('save_payment'))),
              ),
            ]),
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
      line.month = _monthValue(months.firstWhere((m) => m.year == now.year && m.month == now.month,
          orElse: () => months.first));
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(children: [
          DropdownButtonFormField<String>(
            key: Key('collect-type-$i'),
            initialValue: line.typeId,
            isExpanded: true,
            decoration: InputDecoration(
              labelText: t('contribution_type'),
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
              labelText: t('amount'),
              prefixText: '₹ ',
              helperText: hint,
              errorText: _error?.fieldError('lines.$i.amount') ??
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
                labelText: t('month'),
                errorText: _error?.fieldError('lines.$i.period_month'),
                border: const OutlineInputBorder(),
              ),
              items: [
                for (final m in months) DropdownMenuItem(value: _monthValue(m), child: Text(_monthLabel(m))),
              ],
              onChanged: (v) => setState(() => line.month = v),
            ),
          ],
          if (_lines.length > 1)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(onPressed: () => setState(() => _lines.removeAt(i)), child: Text(t('remove'))),
            ),
        ]),
      ),
    );
  }
}
