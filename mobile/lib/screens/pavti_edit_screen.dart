import 'package:flutter/material.dart';

import '../util/money.dart';
import '../widgets/common.dart';

/// Organization Admin: correct the amounts on a pavti (typed 500, should be 400) and its notes. The pavti keeps
/// its number. On a pavti that keeps a balance the difference moves onto or off the balance still owed.
class PavtiEditScreen extends StatefulWidget {
  const PavtiEditScreen({super.key, required this.paymentId});
  final String paymentId;

  @override
  State<PavtiEditScreen> createState() => _PavtiEditScreenState();
}

class _PavtiEditScreenState extends State<PavtiEditScreen> {
  final _form = GlobalKey<FormState>();
  final _amounts = <String, TextEditingController>{};
  final _notes = TextEditingController();
  Map<String, dynamic>? _payment;
  bool _busy = false;

  static final _money = RegExp(r'^\d+(\.\d{1,2})?$');

  @override
  void dispose() {
    for (final c in _amounts.values) {
      c.dispose();
    }
    _notes.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>> _load() async {
    final p = ((await AppScope.read(context).api.get('/payments/${widget.paymentId}/')) as Map).cast<String, dynamic>();
    if (_payment == null) {
      for (final line in (p['lines'] as List? ?? const []).cast<Map>()) {
        _amounts['${line['id']}'] = TextEditingController(text: _plain('${line['amount']}'));
      }
      _notes.text = '${p['notes'] ?? ''}';
      _payment = p;
    }
    return p;
  }

  /// "500.00" -> "500", "750.50" stays.
  static String _plain(String amount) => amount.endsWith('.00') ? amount.substring(0, amount.length - 3) : amount;

  static int _paise(String amount) => (double.parse(amount) * 100).round();

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final app = AppScope.read(context);
    final changed = <String, String>{};
    for (final line in (_payment!['lines'] as List).cast<Map>()) {
      final id = '${line['id']}';
      final now = _amounts[id]!.text.trim();
      if (_paise(now) != _paise('${line['amount']}')) changed[id] = now;
    }
    setState(() => _busy = true);
    try {
      await app.api.post('/payments/${widget.paymentId}/edit/', {
        if (changed.isNotEmpty) 'line_amounts': changed,
        'notes': _notes.text.trim(),
      });
      if (!mounted) return;
      showMessage(context, app.t('saved'));
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
    final t = app.t;
    return Scaffold(
      appBar: AppBar(title: Text(t('edit_pavti'))),
      body: AsyncView<Map<String, dynamic>>(
        load: _load,
        builder: (context, p, _) {
          final lines = (p['lines'] as List? ?? const []).cast<Map>();
          return Form(
            key: _form,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  '${p['receipt']?['receipt_number'] ?? ''} · ${p['payer_name'] ?? ''}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(t('edit_pavti_note'), style: Theme.of(context).textTheme.bodySmall),
                if (p['keeps_balance'] == true) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: Colors.amber.shade50, borderRadius: BorderRadius.circular(8)),
                    child: Text(t('edit_balance_note')),
                  ),
                ],
                const SizedBox(height: 16),
                for (final line in lines)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: TextFormField(
                      key: Key('pavti-amount-${line['id']}'),
                      controller: _amounts['${line['id']}'],
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: InputDecoration(
                        labelText: [
                          line['contribution_type_name'],
                          if (line['period_month'] != null) formatDate('${line['period_month']}').substring(3),
                          if (line['towards_balance'] == true) t('towards_balance'),
                        ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
                        prefixText: '₹ ',
                        border: const OutlineInputBorder(),
                      ),
                      validator: (v) {
                        final text = (v ?? '').trim();
                        if (!_money.hasMatch(text) || _paise(text) == 0) return t('invalid_amount');
                        return null;
                      },
                    ),
                  ),
                TextField(
                  controller: _notes,
                  maxLength: 500,
                  decoration: InputDecoration(labelText: t('notes'), border: const OutlineInputBorder()),
                ),
                const SizedBox(height: 8),
                FilledButton.icon(
                  key: const Key('pavti-save'),
                  onPressed: _busy ? null : _save,
                  icon: const Icon(Icons.check),
                  label: Padding(padding: const EdgeInsets.all(12), child: Text(t('save'))),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
