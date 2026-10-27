import 'package:flutter/material.dart';

import 'common.dart';

/// Only the Organization Admin (and the platform admin) may delete records.
const deletePermission = 'records.admin_edit';

/// Tick rows of a list and delete them together. A long press on a row starts ticking; while anything is
/// ticked a tap ticks too, and [BulkDeleteBar] shows how many, "select all" and the delete button.
mixin BulkSelect<T extends StatefulWidget> on State<T> {
  final Set<String> selected = {};

  /// The rows on screen, for "select all". Set it while building the list.
  List<String> visibleIds = const [];

  /// Goes up after a delete; put it in the list's reload key.
  int bulkVersion = 0;

  bool get selecting => selected.isNotEmpty;

  void toggleSelected(String id) => setState(() => selected.contains(id) ? selected.remove(id) : selected.add(id));

  void clearSelected() => setState(selected.clear);

  void toggleAllVisible() => setState(() {
    if (visibleIds.every(selected.contains)) {
      selected.removeAll(visibleIds);
    } else {
      selected.addAll(visibleIds);
    }
  });

  /// The tick box shown in front of a row while selecting, or null.
  Widget? selectBox(String id) =>
      selecting ? Checkbox(value: selected.contains(id), onChanged: (_) => toggleSelected(id)) : null;

  /// Asks first, then sends the ticked rows to `<path>bulk-delete/`. Each one is deleted as it would be on its
  /// own, and the audit log keeps a copy.
  Future<void> confirmBulkDelete(String path, {String messageKey = 'bulk_confirm'}) async {
    final app = AppScope.read(context);
    final count = '${selected.length}';
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(app.t('bulk_confirm_title', {'count': count})),
        content: Text(app.t(messageKey)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(app.t('cancel'))),
          FilledButton(
            key: const Key('confirm-bulk-delete'),
            style: FilledButton.styleFrom(backgroundColor: Theme.of(ctx).colorScheme.error),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(app.t('delete')),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      final result = (await app.api.post('${path}bulk-delete/', {'ids': selected.toList()})) as Map;
      final failed = (result['failed'] as List?) ?? const [];
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            [
              app.t('bulk_deleted', {'count': '${result['deleted']}'}),
              if (failed.isNotEmpty)
                app.t('bulk_failed', {'count': '${failed.length}', 'reason': '${(failed.first as Map)['message']}'}),
            ].join('\n'),
          ),
        ),
      );
      if (mounted) {
        setState(() {
          selected.clear();
          bulkVersion++;
        });
      }
    } catch (e) {
      if (mounted) messenger.showSnackBar(SnackBar(content: Text(errorText(context, e))));
    }
  }
}

/// "3 selected · Select all · Clear · Delete" above a list while rows are ticked.
class BulkDeleteBar extends StatelessWidget {
  const BulkDeleteBar({super.key, required this.count, required this.onSelectAll, required this.onClear, required this.onDelete});
  final int count;
  final VoidCallback onSelectAll;
  final VoidCallback onClear;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: scheme.errorContainer.withValues(alpha: 0.5),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Row(
          children: [
            IconButton(tooltip: app.t('bulk_clear'), icon: const Icon(Icons.close), onPressed: onClear),
            Expanded(
              child: Text(app.t('bulk_selected', {'count': '$count'}), style: Theme.of(context).textTheme.titleSmall),
            ),
            IconButton(tooltip: app.t('bulk_select_all'), icon: const Icon(Icons.select_all), onPressed: onSelectAll),
            IconButton(
              key: const Key('bulk-delete'),
              tooltip: app.t('delete'),
              icon: Icon(Icons.delete_outline, color: scheme.error),
              onPressed: onDelete,
            ),
          ],
        ),
      ),
    );
  }
}
