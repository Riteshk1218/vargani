import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/checkout.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'receipt_screen.dart';
import 'receipts_screen.dart';

/// Member portal home: totals, what is still due, and online payment.
class MemberHome extends StatelessWidget {
  const MemberHome({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return AsyncView<(Map<String, dynamic>, Map<String, dynamic>)>(
      reloadKey: app.eventId,
      load: () async {
        final me = ((await app.api.get('/portal/me/')) as Map).cast<String, dynamic>();
        final summary =
            ((await app.api.get('/portal/summary/', query: {'event': app.eventId})) as Map).cast<String, dynamic>();
        return (me, summary);
      },
      builder: (context, data, reload) {
        final (me, s) = data;
        final dues = (s['dues'] as List? ?? []).cast<Map>().map((e) => e.cast<String, dynamic>()).toList();
        final byType = (s['by_type'] as List? ?? []).cast<Map>();
        final online = me['online_payments'] == true;
        final person = (me['person'] as Map?) ?? {};
        final text = Theme.of(context).textTheme;
        return ListView(padding: const EdgeInsets.all(12), children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 4, 4, 12),
            child: Text('${person['full_name'] ?? ''}', style: text.headlineSmall),
          ),
          Row(children: [
            Expanded(child: StatCard(label: app.t('total_paid'), amount: '${s['total_paid']}', highlight: true)),
            Expanded(child: StatCard(label: app.t('total_due'), amount: '${s['total_due']}')),
          ]),
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 16, 4, 8),
            child: Text(app.t('my_dues'), style: text.titleMedium),
          ),
          if (dues.isEmpty)
            Card(child: ListTile(leading: const Icon(Icons.celebration_outlined), title: Text(app.t('no_dues'))))
          else
            for (final d in dues)
              Card(
                child: ListTile(
                  title: Text('${d['name']}'),
                  subtitle: Text(
                      '${app.t('expected')} ${formatInr('${d['expected']}')} · ${app.t('paid')} ${formatInr('${d['paid']}')}'),
                  trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text(app.t('due'), style: text.labelSmall),
                    Text(formatInr('${d['due']}'), style: text.titleSmall),
                  ]),
                ),
              ),
          if (online && dues.any((d) => normaliseAmount('${d['due']}') != null)) ...[
            const SizedBox(height: 8),
            FilledButton.icon(
              key: const Key('member-pay'),
              icon: const Icon(Icons.payment),
              label: Padding(padding: const EdgeInsets.all(12), child: Text(app.t('pay_online'))),
              onPressed: () async {
                final paid = await showModalBottomSheet<bool>(
                  context: context,
                  isScrollControlled: true,
                  builder: (_) => AppScope(state: app, child: _PaySheet(dues: dues)),
                );
                if (paid == true) await reload();
              },
            ),
          ],
          if (byType.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 16, 4, 8),
              child: Text(app.t('total_paid'), style: text.titleMedium),
            ),
            Card(
              child: Column(children: [
                for (final b in byType)
                  ListTile(
                    dense: true,
                    title: Text('${b['name']}'),
                    subtitle: Text('${b['event']}'),
                    trailing: Text(formatInr('${b['total']}')),
                  ),
              ]),
            ),
          ],
        ]);
      },
    );
  }
}

class _PaySheet extends StatefulWidget {
  const _PaySheet({required this.dues});
  final List<Map<String, dynamic>> dues;
  @override
  State<_PaySheet> createState() => _PaySheetState();
}

class _PaySheetState extends State<_PaySheet> {
  late final Map<String, TextEditingController> _amounts = {
    for (final d in widget.dues)
      if (normaliseAmount('${d['due']}') != null) '${d['contribution_type']}': TextEditingController(text: '${d['due']}'),
  };
  bool _busy = false;

  Future<void> _pay() async {
    final app = AppScope.read(context);
    final lines = [
      for (final e in _amounts.entries)
        if (normaliseAmount(e.value.text) != null)
          {'contribution_type': e.key, 'amount': normaliseAmount(e.value.text)},
    ];
    if (lines.isEmpty) {
      showMessage(context, app.t('invalid_amount'), error: true);
      return;
    }
    if (!checkoutSupported) {
      showMessage(context, app.t('online_unavailable'), error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      final r = (await app.api.post('/portal/pay/', {'event': app.eventId, 'lines': lines})) as Map;
      final result = await openCheckout((r['checkout'] as Map).cast<String, dynamic>());
      if (!result.ok) {
        if (mounted) showMessage(context, app.t('payment_failed'), error: true);
        return;
      }
      await app.api.post('/portal/pay/verify/', {
        'order_id': result.orderId,
        'payment_id': result.paymentId,
        'signature': result.signature,
      });
      if (!mounted) return;
      showMessage(context, app.t('payment_received'));
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(app.t('pay_online'), style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        for (final d in widget.dues)
          if (_amounts.containsKey('${d['contribution_type']}'))
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: TextField(
                controller: _amounts['${d['contribution_type']}'],
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(
                  labelText: '${d['name']}',
                  prefixText: '₹ ',
                  border: const OutlineInputBorder(),
                ),
              ),
            ),
        FilledButton(
          onPressed: _busy ? null : _pay,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: _busy
                ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : Text(app.t('pay_now')),
          ),
        ),
      ]),
    );
  }
}

class MemberPayments extends StatelessWidget {
  const MemberPayments({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return AsyncView<List<Map<String, dynamic>>>(
      reloadKey: app.eventId,
      load: () async => resultsOf(await app.api.get('/portal/payments/', query: {'event': app.eventId})),
      builder: (context, items, _) => items.isEmpty
          ? EmptyState(icon: Icons.payments_outlined, text: app.t('no_payments'))
          : ListView.separated(
              itemCount: items.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final p = items[i];
                final lines = (p['lines'] as List? ?? []).cast<Map>();
                final receipt = p['receipt'] as Map?;
                return ListTile(
                  title: Text(lines.map((l) => l['contribution_type_name']).join(', ')),
                  subtitle: Text('${formatDate('${p['paid_at']}')} · ${modeLabel(app, '${p['mode']}')}'
                      '${receipt != null ? ' · ${receipt['receipt_number']}' : ''}'),
                  trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text(formatInr('${p['amount']}'), style: Theme.of(context).textTheme.titleSmall),
                    if (p['status'] != 'successful') StatusChip('${p['status']}'),
                  ]),
                  onTap: receipt == null
                      ? null
                      : () => Navigator.push(context,
                          MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${receipt['id']}', portal: true))),
                );
              },
            ),
    );
  }
}

class MemberReceipts extends StatelessWidget {
  const MemberReceipts({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return AsyncView<List<Map<String, dynamic>>>(
      reloadKey: app.eventId,
      load: () async => resultsOf(await app.api.get('/portal/receipts/', query: {'event': app.eventId})),
      builder: (context, items, _) => items.isEmpty
          ? EmptyState(icon: Icons.receipt_long, text: app.t('no_receipts'))
          : ReceiptList(
              items: items,
              onTap: (r) => Navigator.push(
                  context, MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${r['id']}', portal: true))),
            ),
    );
  }
}
