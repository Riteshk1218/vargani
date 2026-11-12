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

  /// Pavtis created by this user only (null: everyone).
  Map<String, dynamic>? _creator;

  Future<void> _pickCreator() async {
    final app = AppScope.read(context);
    final t = app.t;
    List<Map<String, dynamic>> creators;
    try {
      creators = resultsOf(await app.api.get('/receipts/creators/', query: {'event': app.eventId}));
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
      return;
    }
    if (!mounted) return;
    final picked = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      builder: (context) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            ListTile(title: Text(t('created_by'), style: Theme.of(context).textTheme.titleMedium)),
            ListTile(
              key: const Key('creator-everyone'),
              leading: Icon(_creator == null ? Icons.radio_button_checked : Icons.radio_button_off),
              title: Text(t('everyone')),
              onTap: () => Navigator.pop(context, const <String, dynamic>{}),
            ),
            for (final c in creators)
              ListTile(
                key: Key('creator-${c['id']}'),
                leading: Icon(_creator?['id'] == c['id'] ? Icons.radio_button_checked : Icons.radio_button_off),
                title: Text('${c['name']}'),
                onTap: () => Navigator.pop(context, c),
              ),
          ],
        ),
      ),
    );
    if (picked == null) return;
    setState(() => _creator = picked.isEmpty ? null : picked);
  }

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
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 0, 12, 4),
          child: Align(
            alignment: Alignment.centerLeft,
            child: InputChip(
              key: const Key('receipts-created-by'),
              avatar: const Icon(Icons.person_outline, size: 18),
              label: Text('${app.t('created_by')}: ${_creator == null ? app.t('everyone') : _creator!['name']}'),
              selected: _creator != null,
              onPressed: _pickCreator,
              onDeleted: _creator == null ? null : () => setState(() => _creator = null),
            ),
          ),
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
            reloadKey: '${app.eventId}-${_query.key}-${_creator?['id']}-$bulkVersion',
            load: () async => resultsOf(
              await app.api.get(
                '/receipts/',
                query: {
                  'event': app.eventId,
                  ..._query.query,
                  'created_by': _creator?['id']?.toString(),
                  'page_size': '100',
                },
              ),
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
                            ).then((_) => reload()),
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
