import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/bulk_delete.dart';
import '../widgets/common.dart';
import '../widgets/list_tools.dart';
import 'receipt_screen.dart';

/// Receipts in the current event (collectors see only their own; the API filters).
class ReceiptsScreen extends StatefulWidget {
  const ReceiptsScreen({super.key});

  @override
  State<ReceiptsScreen> createState() => _ReceiptsScreenState();
}

class _ReceiptsScreenState extends State<ReceiptsScreen> with BulkSelect {
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
        if (selecting)
          BulkDeleteBar(
            count: selected.length,
            onSelectAll: toggleAllVisible,
            onClear: clearSelected,
            onDelete: () => confirmBulkDelete('/receipts/', messageKey: 'bulk_confirm_collections'),
          ),
        Expanded(
          child: AsyncView<List<Map<String, dynamic>>>(
            reloadKey: '${app.eventId}-${_query.key}-$bulkVersion',
            load: () async => resultsOf(
              await app.api.get('/receipts/', query: {'event': app.eventId, ..._query.query, 'page_size': '100'}),
            ),
            builder: (context, items, reload) {
              visibleIds = [for (final r in items) if (r['status'] == 'issued') '${r['id']}'];
              return items.isEmpty
                  ? EmptyState(icon: Icons.receipt_long, text: app.t('no_receipts'))
                  : ReceiptList(
                      items: items,
                      leading: selectBox,
                      onLongPress: app.can(deletePermission) ? (r) => toggleSelected('${r['id']}') : null,
                      onTap: (r) => selecting
                          ? (r['status'] == 'issued' ? toggleSelected('${r['id']}') : null)
                          : Navigator.push(
                              context,
                              MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${r['id']}')),
                            ),
                    );
            },
          ),
        ),
      ],
    );
  }
}

class ReceiptList extends StatelessWidget {
  const ReceiptList({super.key, required this.items, required this.onTap, this.leading, this.onLongPress});
  final List<Map<String, dynamic>> items;
  final void Function(Map<String, dynamic>) onTap;

  /// A tick box in front of a row while selecting (see BulkSelect), by receipt id.
  final Widget? Function(String id)? leading;
  final void Function(Map<String, dynamic>)? onLongPress;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.only(bottom: 24),
      itemCount: items.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, i) {
        final r = items[i];
        final issued = r['status'] == 'issued';
        return ListTile(
          leading: issued ? leading?.call('${r['id']}') : null,
          onLongPress: issued && onLongPress != null ? () => onLongPress!(r) : null,
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
