import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'receipt_screen.dart';

/// Receipts in the current event (collectors see only their own; the API filters).
class ReceiptsScreen extends StatelessWidget {
  const ReceiptsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return AsyncView<List<Map<String, dynamic>>>(
      reloadKey: app.eventId,
      load: () async => resultsOf(await app.api.get('/receipts/', query: {'event': app.eventId})),
      builder: (context, items, reload) => items.isEmpty
          ? EmptyState(icon: Icons.receipt_long, text: app.t('no_receipts'))
          : ReceiptList(items: items, onTap: (r) => Navigator.push(
                context, MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${r['id']}')))),
    );
  }
}

class ReceiptList extends StatelessWidget {
  const ReceiptList({super.key, required this.items, required this.onTap});
  final List<Map<String, dynamic>> items;
  final void Function(Map<String, dynamic>) onTap;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.only(bottom: 24),
      itemCount: items.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, i) {
        final r = items[i];
        return ListTile(
          title: Text('${r['payer_name'] ?? ''}'),
          subtitle: Text('${r['receipt_number']} · ${formatDate('${r['issued_at']}')}'),
          trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text(formatInr('${r['amount']}'), style: Theme.of(context).textTheme.titleSmall),
            if (r['status'] != 'issued') StatusChip('${r['status']}'),
          ]),
          onTap: () => onTap(r),
        );
      },
    );
  }
}
