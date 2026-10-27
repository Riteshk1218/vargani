import 'package:flutter/material.dart';

import '../util/money.dart';
import 'common.dart';

String todayIso() => isoDay(DateTime.now());

/// One sort choice: the API ordering field (without "-") and its label key.
class SortOption {
  const SortOption(this.field, this.labelKey);
  final String field;
  final String labelKey;
}

/// Date range and sort order of a list. [query] goes straight into the list request.
class ListQuery {
  const ListQuery({this.dateFrom, this.dateTo, required this.ordering});
  final String? dateFrom;
  final String? dateTo;
  final String ordering;

  bool get descending => ordering.startsWith('-');
  String get field => descending ? ordering.substring(1) : ordering;
  bool get filtered => dateFrom != null || dateTo != null;

  Map<String, String> get query => {
    'ordering': ordering,
    'date_from': ?dateFrom,
    'date_to': ?dateTo,
  };

  ListQuery copyWith({String? dateFrom, String? dateTo, String? ordering, bool clearDates = false}) => ListQuery(
    dateFrom: clearDates ? null : (dateFrom ?? this.dateFrom),
    dateTo: clearDates ? null : (dateTo ?? this.dateTo),
    ordering: ordering ?? this.ordering,
  );

  /// Reload key for [AsyncView].
  String get key => '$dateFrom|$dateTo|$ordering';
}

/// From / To dates, a Today shortcut, the field to sort by and ascending / descending.
class ListToolsBar extends StatelessWidget {
  const ListToolsBar({super.key, required this.value, required this.onChanged, this.sortOptions = const []});
  final ListQuery value;
  final ValueChanged<ListQuery> onChanged;
  final List<SortOption> sortOptions;

  Future<String?> _pick(BuildContext context, String? current) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.tryParse(current ?? '') ?? now,
      firstDate: DateTime(now.year - 5),
      lastDate: DateTime(now.year + 1, 12, 31),
    );
    return picked == null ? null : isoDay(picked);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppScope.of(context).t;
    final today = todayIso();
    final isToday = value.dateFrom == today && value.dateTo == today;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Wrap(
        spacing: 8,
        runSpacing: 4,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          ActionChip(
            key: const Key('list-from'),
            avatar: const Icon(Icons.event, size: 18),
            label: Text(value.dateFrom == null ? t('list_from') : '${t('list_from')} ${formatDate(value.dateFrom)}'),
            onPressed: () async {
              final picked = await _pick(context, value.dateFrom);
              if (picked == null) return;
              final to = value.dateTo != null && value.dateTo!.compareTo(picked) < 0 ? picked : value.dateTo;
              onChanged(value.copyWith(dateFrom: picked, dateTo: to));
            },
          ),
          ActionChip(
            key: const Key('list-to'),
            avatar: const Icon(Icons.event, size: 18),
            label: Text(value.dateTo == null ? t('list_to') : '${t('list_to')} ${formatDate(value.dateTo)}'),
            onPressed: () async {
              final picked = await _pick(context, value.dateTo ?? value.dateFrom);
              if (picked == null) return;
              final from = value.dateFrom != null && value.dateFrom!.compareTo(picked) > 0 ? picked : value.dateFrom;
              onChanged(value.copyWith(dateFrom: from, dateTo: picked));
            },
          ),
          FilterChip(
            key: const Key('list-today'),
            label: Text(t('today')),
            selected: isToday,
            onSelected: (_) => onChanged(value.copyWith(dateFrom: today, dateTo: today)),
          ),
          if (value.filtered)
            InputChip(
              key: const Key('list-all-dates'),
              label: Text(t('list_all_dates')),
              onDeleted: () => onChanged(value.copyWith(clearDates: true)),
              onPressed: () => onChanged(value.copyWith(clearDates: true)),
            ),
          if (sortOptions.isNotEmpty) ...[
            PopupMenuButton<String>(
              key: const Key('list-sort'),
              tooltip: t('list_sort_by'),
              onSelected: (f) => onChanged(value.copyWith(ordering: value.descending ? '-$f' : f)),
              itemBuilder: (_) => [
                for (final o in sortOptions)
                  CheckedPopupMenuItem(value: o.field, checked: o.field == value.field, child: Text(t(o.labelKey))),
              ],
              child: Chip(
                avatar: const Icon(Icons.sort, size: 18),
                label: Text(
                  '${t('list_sort_by')}: ${t(sortOptions.firstWhere((o) => o.field == value.field, orElse: () => sortOptions.first).labelKey)}',
                ),
              ),
            ),
            IconButton.outlined(
              key: const Key('list-direction'),
              tooltip: value.descending ? t('list_descending') : t('list_ascending'),
              icon: Icon(value.descending ? Icons.arrow_downward : Icons.arrow_upward, size: 18),
              onPressed: () => onChanged(value.copyWith(ordering: value.descending ? value.field : '-${value.field}')),
            ),
          ],
        ],
      ),
    );
  }
}

/// "Created 27-Oct-2026, 10:30 AM · by Ritesh" under a row.
class CreatedLine extends StatelessWidget {
  const CreatedLine(this.row, {super.key});
  final Map row;

  @override
  Widget build(BuildContext context) {
    final t = AppScope.of(context).t;
    final at = row['created_at']?.toString();
    if (at == null) return const SizedBox.shrink();
    final by = row['created_by_name']?.toString();
    return Text(
      [
        t('list_created', {'date': formatStamp(at)}),
        if (by != null && by.isNotEmpty) t('list_by', {'name': by}),
      ].join(' · '),
      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.outline),
    );
  }
}
