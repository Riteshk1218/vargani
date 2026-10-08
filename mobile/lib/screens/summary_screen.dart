import 'package:flutter/material.dart';

import '../util/money.dart';
import '../widgets/common.dart';

/// Collection − approved expenses = balance, one card per event of the current event's financial year.
class SummaryScreen extends StatelessWidget {
  const SummaryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    final year = app.event?['financial_year']?.toString();
    return Scaffold(
      appBar: AppBar(title: Text(t('financial_summary'))),
      body: AsyncView<Map<String, dynamic>>(
        reloadKey: year,
        load: () async =>
            ((await app.api.get('/finance/summary/', query: {'financial_year': year})) as Map).cast<String, dynamic>(),
        builder: (context, d, _) {
          final events = (d['events'] as List? ?? []).cast<Map>();
          if (events.isEmpty) return EmptyState(icon: Icons.balance, text: t('no_events'));
          return ListView(
            padding: const EdgeInsets.all(12),
            children: [for (final e in events) _EventCard(row: e)],
          );
        },
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  const _EventCard({required this.row});
  final Map row;

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    final text = Theme.of(context).textTheme;
    final balance = '${row['balance']}';
    Widget line(String label, String amount, {bool bold = false, Color? color}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Expanded(child: Text(label, style: bold ? text.titleMedium : text.bodyMedium)),
          Text(
            formatInr(amount),
            style: (bold ? text.titleMedium : text.bodyMedium)?.copyWith(
              color: color,
              fontWeight: bold ? FontWeight.bold : null,
            ),
          ),
        ],
      ),
    );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${(row['event'] as Map)['name']}', style: text.titleLarge),
            Text('${t('financial_year')} ${(row['financial_year'] as Map)['label']}', style: text.bodySmall),
            const Divider(height: 20),
            line(t('collection'), '${row['collection']}'),
            if (double.tryParse('${row['other_income']}') != 0)
              line('+ ${t('other_income')}', '${row['other_income']}'),
            line('− ${t('approved_expenses')}', '${row['approved_expenses']}'),
            const Divider(height: 16),
            line(
              '= ${t('balance')}',
              balance,
              bold: true,
              color: balance.startsWith('-') ? Theme.of(context).colorScheme.error : Colors.green.shade700,
            ),
            if (double.tryParse('${row['pending_expenses']}') != 0)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  t('pending_not_counted', {'amount': formatInr('${row['pending_expenses']}')}),
                  style: text.bodySmall,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
