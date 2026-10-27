import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import '../widgets/list_tools.dart';
import 'followups_screen.dart' show PavtiChips;
import 'receipt_screen.dart';

const paymentSorts = [
  SortOption('paid_at', 'list_date'),
  SortOption('created_at', 'list_created_at'),
  SortOption('amount', 'list_amount'),
  SortOption('payer__full_name', 'list_name'),
  SortOption('balance_due', 'still_owed'),
];

/// Payments in the current event, opened from a dashboard card with its filters (status, mode, pavti,
/// collector) and days already chosen. Shows who recorded each one and when.
class PaymentsListScreen extends StatefulWidget {
  const PaymentsListScreen({super.key, required this.title, this.filters = const {}, this.dateFrom, this.dateTo});
  final String title;
  final Map<String, String> filters;
  final String? dateFrom;
  final String? dateTo;

  @override
  State<PaymentsListScreen> createState() => _PaymentsListScreenState();
}

class _PaymentsListScreenState extends State<PaymentsListScreen> {
  late ListQuery _query = ListQuery(dateFrom: widget.dateFrom, dateTo: widget.dateTo, ordering: '-paid_at');

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          ListToolsBar(value: _query, onChanged: (q) => setState(() => _query = q), sortOptions: paymentSorts),
          Expanded(
            child: AsyncView<Map<String, dynamic>>(
              reloadKey: '${app.eventId}-${_query.key}',
              load: () async => ((await app.api.get(
                '/payments/',
                query: {'event': app.eventId, ...widget.filters, ..._query.query, 'page_size': '100'},
              )) as Map).cast<String, dynamic>(),
              builder: (context, data, reload) {
                final rows = resultsOf(data);
                if (rows.isEmpty) return EmptyState(icon: Icons.payments_outlined, text: t('no_payments'));
                final total = rows
                    .where((p) => p['status'] == 'successful')
                    .fold<double>(0, (sum, p) => sum + (double.tryParse('${p['amount']}') ?? 0));
                return ListView.separated(
                  key: const Key('payments-list'),
                  padding: const EdgeInsets.only(bottom: 24),
                  itemCount: rows.length + 1,
                  separatorBuilder: (_, _) => const Divider(height: 1),
                  itemBuilder: (context, i) {
                    if (i == 0) {
                      return ListTile(
                        dense: true,
                        title: Text(t('list_count', {'count': '${data['count'] ?? rows.length}'})),
                        trailing: Text(
                          formatInr(total.toStringAsFixed(2)),
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                      );
                    }
                    final p = rows[i - 1];
                    final receipt = p['receipt'] as Map?;
                    return ListTile(
                      title: Text('${p['payer_name']}'),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            [
                              formatStamp('${p['paid_at']}'),
                              modeLabel(app, '${p['mode']}'),
                              receipt?['receipt_number'],
                            ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
                          ),
                          CreatedLine(p),
                          PavtiChips(p),
                        ],
                      ),
                      trailing: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(formatInr('${p['amount']}'), style: Theme.of(context).textTheme.titleSmall),
                          if (p['status'] != 'successful') StatusChip('${p['status']}'),
                        ],
                      ),
                      onTap: receipt == null
                          ? null
                          : () => Navigator.push(
                              context,
                              MaterialPageRoute(builder: (_) => ReceiptScreen(receiptId: '${receipt['id']}')),
                            ).then((_) => reload()),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
