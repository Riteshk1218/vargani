import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../util/files.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'org_picker_screen.dart';

/// A receipt (pavti) as issued, built from the snapshot the server stored at issue time.
class ReceiptScreen extends StatefulWidget {
  const ReceiptScreen({super.key, required this.receiptId, this.justIssued = false, this.portal = false});
  final String receiptId;
  final bool justIssued;

  /// Members read receipts through the portal endpoints.
  final bool portal;

  @override
  State<ReceiptScreen> createState() => _ReceiptScreenState();
}

class _ReceiptScreenState extends State<ReceiptScreen> {
  bool _busy = false;

  String get _base => widget.portal ? '/portal/receipts/${widget.receiptId}' : '/receipts/${widget.receiptId}';

  Future<void> _share() async {
    final app = AppScope.read(context);
    setState(() => _busy = true);
    try {
      final r = (await app.api.post('/receipts/${widget.receiptId}/share/')) as Map;
      final url = Uri.parse('${r['whatsapp_url']}');
      if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
        if (mounted) showMessage(context, '${r['whatsapp_text']}');
      }
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pdf(String number) async {
    final app = AppScope.read(context);
    setState(() => _busy = true);
    try {
      final bytes = await app.api.getBytes('$_base/pdf/');
      await openPdfBytes(bytes, 'receipt-$number.pdf');
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    return Scaffold(
      appBar: AppBar(title: Text(widget.justIssued ? t('receipt_issued') : t('receipts'))),
      body: AsyncView<Map<String, dynamic>>(
        load: () async => ((await app.api.get('$_base/')) as Map).cast<String, dynamic>(),
        builder: (context, r, _) {
          final s = (r['snapshot'] as Map?)?.cast<String, dynamic>() ?? {};
          final org = (s['organization'] as Map?) ?? {};
          final person = (s['person'] as Map?) ?? {};
          final event = (s['event'] as Map?) ?? {};
          final lines = (s['lines'] as List? ?? []).cast<Map>();
          final number = '${r['receipt_number']}';
          final text = Theme.of(context).textTheme;
          Widget row(String k, Object? v) => (v == null || '$v'.isEmpty)
              ? const SizedBox.shrink()
              : Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(width: 120, child: Text(k, style: text.bodySmall)),
                      Expanded(child: Text('$v', style: text.bodyMedium)),
                    ],
                  ),
                );
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (widget.justIssued)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green.shade600, size: 32),
                      const SizedBox(width: 8),
                      Text(t('receipt_issued'), style: text.titleLarge),
                    ],
                  ),
                ),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          OrgAvatar(name: '${org['name'] ?? ''}', logoUrl: r['logo_url'] as String?, radius: 24),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${org['name'] ?? ''}', style: text.titleMedium),
                                if ('${org['address'] ?? ''}'.isNotEmpty)
                                  Text('${org['address']}', style: text.bodySmall),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 24),
                      Row(
                        children: [
                          Expanded(child: Text('${t('receipt_no')} $number', style: text.titleSmall)),
                          StatusChip('${r['status']}'),
                        ],
                      ),
                      const SizedBox(height: 8),
                      row(t('payer'), person['anonymous'] == true ? t('anonymous') : person['name']),
                      row(t('mobile'), person['mobile']),
                      row(t('event'), event['name']),
                      row(t('financial_year'), s['financial_year']),
                      row(t('date_time'), formatStamp('${s['paid_at'] ?? r['issued_at']}')),
                      row(t('payment_mode'), modeLabel(app, '${s['mode'] ?? r['mode']}')),
                      row(t('reference'), s['reference_number']),
                      row(t('collected_by'), s['collector']),
                      const Divider(height: 24),
                      for (final l in lines)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  [
                                    l['contribution_type'],
                                    l['fund'],
                                    if (l['period_month'] != null) formatDate('${l['period_month']}').substring(3),
                                  ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
                                ),
                              ),
                              Text(formatInr('${l['amount']}')),
                            ],
                          ),
                        ),
                      const Divider(height: 24),
                      Row(
                        children: [
                          Expanded(child: Text(t('total'), style: text.titleMedium)),
                          Text(
                            formatInr('${s['total'] ?? r['amount']}'),
                            style: text.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      if ('${s['thank_you_message'] ?? ''}'.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Text(
                          '${s['thank_you_message']}',
                          style: text.bodyMedium?.copyWith(fontStyle: FontStyle.italic),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (!widget.portal && app.can('receipts.share') && r['status'] == 'issued')
                FilledButton.icon(
                  key: const Key('receipt-whatsapp'),
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF25D366),
                    foregroundColor: Colors.white,
                  ),
                  onPressed: _busy ? null : _share,
                  icon: const Icon(Icons.share),
                  label: Padding(padding: const EdgeInsets.all(12), child: Text(t('share_whatsapp'))),
                ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                key: const Key('receipt-pdf'),
                onPressed: _busy ? null : () => _pdf(number),
                icon: const Icon(Icons.picture_as_pdf_outlined),
                label: Padding(padding: const EdgeInsets.all(12), child: Text(t('open_pdf'))),
              ),
              if (widget.justIssued) ...[
                const SizedBox(height: 8),
                TextButton(onPressed: () => Navigator.pop(context), child: Text(t('new_collection'))),
              ],
            ],
          );
        },
      ),
    );
  }
}
