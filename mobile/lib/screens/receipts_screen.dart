import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import '../widgets/list_tools.dart';
import 'receipt_screen.dart';

/// Receipts in the current event (collectors see only their own; the API filters).
class ReceiptsScreen extends StatefulWidget {
  const ReceiptsScreen({super.key});

  @override
  State<ReceiptsScreen> createState() => _ReceiptsScreenState();
}

class _ReceiptsScreenState extends State<ReceiptsScreen> {
  ListQuery _query = const ListQuery(ordering: '-issued_at');

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Column(
      children: [
        ListToolsBar(
          value: _query,
          onChanged: (q) => setState(() => _query = q),
          sortOptions: const [
            SortOption('issued_at', 'list_date'),
            SortOption('sequence', 'list_receipt_number'),
            SortOption('payment__amount', 'list_amount'),
            SortOption('payment__payer__full_name', 'list_name'),
          ],
        ),
        Expanded(
          child: AsyncView<List<Map<String, dynamic>>>(
            reloadKey: '${app.eventId}-${_query.key}',
            load: () async => resultsOf(
              await app.api.get('/receipts/', query: {'event': app.eventId, ..._query.query, 'page_size': '100'}),
            ),
            builder: (context, items, reload) => items.isEmpty
                ? EmptyState(icon: Icons.receipt_long, text: app.t('no_receipts'))
                : ReceiptList(
                    items: items,
                    onTap: (r) => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${r['id']}')),
                    ),
                  ),
          ),
        ),
      ],
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
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${r['receipt_number']} · ${formatStamp('${r['paid_at'] ?? r['issued_at']}')}'),
              if (r['created_at'] != null) CreatedLine(r),
            ],
          ),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(formatInr('${r['amount']}'), style: Theme.of(context).textTheme.titleSmall),
              if (r['status'] != 'issued') StatusChip('${r['status']}'),
            ],
          ),
          onTap: () => onTap(r),
        );
      },
    );
  }
}
