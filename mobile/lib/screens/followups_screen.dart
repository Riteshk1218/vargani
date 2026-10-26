import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'collect_screen.dart' show collectionModes, modesNeedingReference;

/// Door-to-door follow-up: one pavti per house, updated on every later visit instead of making a new one.

String _isoDate(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

DateTime _today() {
  final now = DateTime.now();
  return DateTime(now.year, now.month, now.day);
}

/// Picks a follow-up date (today or later). Returns "YYYY-MM-DD" or null when cancelled.
Future<String?> pickFollowUpDate(BuildContext context, String? current) async {
  final today = _today();
  var initial = DateTime.tryParse(current ?? '') ?? today.add(const Duration(days: 1));
  if (initial.isBefore(today)) initial = today.add(const Duration(days: 1));
  final picked = await showDatePicker(
    context: context,
    initialDate: initial,
    firstDate: today,
    lastDate: today.add(const Duration(days: 365)),
  );
  return picked == null ? null : _isoDate(picked);
}

/// A tappable field showing the follow-up date.
class FollowUpDateField extends StatelessWidget {
  const FollowUpDateField({super.key, required this.value, required this.onChanged, this.label, this.error});
  final String? value;
  final ValueChanged<String> onChanged;
  final String? label;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final t = AppScope.of(context).t;
    return InkWell(
      onTap: () async {
        final picked = await pickFollowUpDate(context, value);
        if (picked != null) onChanged(picked);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label ?? t('follow_up_date'),
          helperText: t('follow_up_hint'),
          errorText: error,
          border: const OutlineInputBorder(),
          suffixIcon: const Icon(Icons.event),
        ),
        child: Text(value == null ? t('choose_date') : formatDate(value)),
      ),
    );
  }
}

/// Unpaid / partly paid badge and the follow-up date of a pavti that still has money owed.
class PavtiChips extends StatelessWidget {
  const PavtiChips(this.payment, {super.key});
  final Map payment;

  @override
  Widget build(BuildContext context) {
    final t = AppScope.of(context).t;
    final scheme = Theme.of(context).colorScheme;
    final status = payment['pavti_status'];
    if (status == null || status == 'paid') return const SizedBox.shrink();
    final state = payment['follow_up_state'];
    final date = payment['follow_up_on']?.toString();
    Widget chip(String text, Color color) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(10)),
      child: Text(text, style: Theme.of(context).textTheme.labelSmall),
    );
    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: [
        chip(status == 'unpaid' ? t('pavti_unpaid') : t('pavti_partly_paid'), Colors.amber.shade100),
        if (date != null)
          chip(
            state == 'overdue'
                ? t('overdue_since', {'date': formatDate(date)})
                : state == 'today'
                ? t('due_today')
                : t('follow_up_on', {'date': formatDate(date)}),
            state == 'overdue' ? scheme.errorContainer : scheme.surfaceContainerHighest,
          ),
      ],
    );
  }
}

/// Dashboard cards: pavtis overdue and due today. Each opens the matching list.
class FollowUpCards extends StatelessWidget {
  const FollowUpCards({super.key, required this.followUps, required this.onReturn});
  final Map followUps;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final t = AppScope.of(context).t;
    final scheme = Theme.of(context).colorScheme;
    Widget card(String key, String label, Object? count, String filter, Color? color) => Expanded(
      child: Card(
        color: color,
        child: InkWell(
          key: Key('follow-up-$key'),
          borderRadius: BorderRadius.circular(12),
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => PavtiListScreen(filter: filter, title: label)),
          ).then((_) => onReturn()),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.labelMedium),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Text(
                      '${count ?? 0}',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const Spacer(),
                    const Icon(Icons.chevron_right),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
    final overdue = followUps['overdue'] as int? ?? 0;
    final today = followUps['due_today'] as int? ?? 0;
    return Column(
      children: [
        Row(
          children: [
            card('overdue', t('overdue'), overdue, 'overdue', overdue > 0 ? scheme.errorContainer : null),
            card('today', t('due_today'), today, 'today', today > 0 ? Colors.amber.shade100 : null),
          ],
        ),
        Card(
          child: ListTile(
            key: const Key('follow-up-owing'),
            leading: const Icon(Icons.pending_actions),
            title: Text(t('pavtis_owing')),
            subtitle: Text('${formatInr('${followUps['balance'] ?? '0'}')} ${t('still_owed')}'),
            trailing: Text('${followUps['owing'] ?? 0}', style: Theme.of(context).textTheme.titleMedium),
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => PavtiListScreen(filter: 'owing', title: t('pavtis_owing'))),
            ).then((_) => onReturn()),
          ),
        ),
      ],
    );
  }
}

/// Pavtis to follow up: `overdue`, `today` or `owing` (all not fully paid).
class PavtiListScreen extends StatelessWidget {
  const PavtiListScreen({super.key, required this.filter, required this.title});
  final String filter;
  final String title;

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: AsyncView<List<Map<String, dynamic>>>(
        reloadKey: app.eventId,
        load: () async => resultsOf(
          await app.api.get(
            '/payments/',
            query: {
              'event': app.eventId,
              if (filter == 'owing') 'pavti': 'owing' else 'follow_up': filter,
              'ordering': 'follow_up_on',
              'page_size': '100',
            },
          ),
        ),
        builder: (context, rows, reload) {
          if (rows.isEmpty) return EmptyState(icon: Icons.check_circle_outline, text: t('no_follow_ups'));
          return ListView(
            padding: const EdgeInsets.all(12),
            children: [
              for (final p in rows)
                Card(
                  child: ListTile(
                    title: Text('${p['payer_name']}'),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          [
                            (p['receipt'] as Map?)?['receipt_number'],
                            p['payer_mobile'],
                          ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
                        ),
                        const SizedBox(height: 4),
                        PavtiChips(p),
                      ],
                    ),
                    trailing: Text(
                      formatInr('${p['balance_due']}'),
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    onTap: () async {
                      final saved = await Navigator.push<bool>(
                        context,
                        MaterialPageRoute(builder: (_) => PavtiVisitScreen(payment: p)),
                      );
                      if (saved == true) reload();
                    },
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

/// A later visit to a house: add the money that came now to the same pavti, or just move the follow-up date.
/// No new pavti is made. Pops with true when saved.
class PavtiVisitScreen extends StatefulWidget {
  const PavtiVisitScreen({super.key, required this.payment});
  final Map payment;

  @override
  State<PavtiVisitScreen> createState() => _PavtiVisitScreenState();
}

class _PavtiVisitScreenState extends State<PavtiVisitScreen> {
  final _received = TextEditingController();
  final _reference = TextEditingController();
  late String _mode;
  String? _followUp;
  bool _saving = false;
  ApiException? _error;

  Map get _p => widget.payment;
  String get _owed => '${_p['balance_due'] ?? '0'}';

  @override
  void initState() {
    super.initState();
    final amount = double.tryParse('${_p['amount']}') ?? 0;
    _mode = amount > 0 ? '${_p['mode']}' : 'cash';
    if (!collectionModes.contains(_mode)) _mode = 'cash';
    final current = _p['follow_up_on']?.toString();
    final today = _isoDate(_today());
    _followUp = current != null && current.compareTo(today) >= 0
        ? current
        : _isoDate(_today().add(const Duration(days: 1)));
  }

  /// What was typed, or "0" when left empty (nobody paid today). Null when not a valid amount.
  String? get _amount {
    final raw = _received.text.trim();
    if (raw.isEmpty) return '0';
    if (RegExp(r'^0+(\.0{1,2})?$').hasMatch(raw)) return '0';
    return normaliseAmount(raw);
  }

  bool get _paysAll {
    final a = double.tryParse(_amount ?? '');
    return a != null && a >= (double.tryParse(_owed) ?? 0);
  }

  Future<void> _save() async {
    final app = AppScope.read(context);
    final t = app.t;
    final amount = _amount;
    if (amount == null || (double.tryParse(amount) ?? 0) > (double.tryParse(_owed) ?? 0)) {
      showMessage(context, t('received_too_much'), error: true);
      return;
    }
    final paying = (double.tryParse(amount) ?? 0) > 0;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await app.api.post('/payments/${_p['id']}/visit/', {
        'received': amount,
        'follow_up_on': _paysAll ? null : _followUp,
        if (paying) 'mode': _mode,
        if (paying) 'reference_number': _reference.text.trim(),
      });
      if (!mounted) return;
      showMessage(context, _paysAll ? t('pavti_now_paid') : t('saved'));
      Navigator.pop(context, true);
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
    final paying = (double.tryParse(_amount ?? '') ?? 0) > 0;
    return Scaffold(
      appBar: AppBar(title: Text(t('update_pavti'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: Colors.amber.shade50,
            child: ListTile(
              title: Text('${_p['payer_name']}'),
              subtitle: Text(
                [
                  (_p['receipt'] as Map?)?['receipt_number'],
                  '${formatInr(_owed)} ${t('still_owed')}',
                ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('visit-received'),
            controller: _received,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: t('received_now'),
              prefixText: '₹ ',
              hintText: '0',
              helperText: t('visit_received_hint'),
              errorText: _error?.fieldError('received'),
              border: const OutlineInputBorder(),
            ),
            onChanged: (_) => setState(() {}),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              key: const Key('visit-paid-in-full'),
              onPressed: () => setState(() => _received.text = _owed),
              child: Text('${t('paid_in_full')} (${formatInr(_owed)})'),
            ),
          ),
          if (paying) ...[
            Text(t('payment_mode'), style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final m in collectionModes)
                  ChoiceChip(
                    label: Text(modeLabel(app, m)),
                    selected: _mode == m,
                    onSelected: (_) => setState(() => _mode = m),
                  ),
              ],
            ),
            if (modesNeedingReference.contains(_mode)) ...[
              const SizedBox(height: 12),
              TextField(
                controller: _reference,
                decoration: InputDecoration(
                  labelText: t('reference'),
                  errorText: _error?.fieldError('reference_number'),
                  border: const OutlineInputBorder(),
                ),
              ),
            ],
            const SizedBox(height: 16),
          ],
          if (_paysAll)
            Card(
              color: Theme.of(context).colorScheme.secondaryContainer,
              child: ListTile(leading: const Icon(Icons.check_circle), title: Text(t('pavti_will_be_paid'))),
            )
          else
            FollowUpDateField(
              label: t('next_follow_up'),
              value: _followUp,
              error: _error?.fieldError('follow_up_on'),
              onChanged: (v) => setState(() => _followUp = v),
            ),
          const SizedBox(height: 16),
          FilledButton.icon(
            key: const Key('visit-save'),
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.check),
            label: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(_paysAll ? t('mark_paid') : (paying ? t('save_payment') : t('save_follow_up'))),
            ),
          ),
        ],
      ),
    );
  }
}
