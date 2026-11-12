import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/common.dart';
import 'collect_screen.dart' show collectionModes, modesNeedingReference;

/// Edit a pavti in place: the amount of each line, the payment mode, reference and notes. The pavti keeps its
/// number. Open to the person who created it and to the Organization Admin (the server checks; `can_edit`).
class PavtiEditScreen extends StatefulWidget {
  const PavtiEditScreen({super.key, required this.paymentId, required this.receiptNumber});
  final String paymentId;
  final String receiptNumber;

  @override
  State<PavtiEditScreen> createState() => _PavtiEditScreenState();
}

class _PavtiEditScreenState extends State<PavtiEditScreen> {
  Map<String, dynamic>? _payment;
  List<Map<String, dynamic>> _lines = [];
  final List<TextEditingController> _amounts = [];
  final _reference = TextEditingController();
  final _notes = TextEditingController();
  String _mode = 'cash';
  bool _busy = false;
  ApiException? _error;

  @override
  void dispose() {
    for (final c in _amounts) {
      c.dispose();
    }
    _reference.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>> _load() async {
    if (_payment != null) return _payment!;
    final app = AppScope.read(context);
    final p = ((await app.api.get('/payments/${widget.paymentId}/')) as Map).cast<String, dynamic>();
    _payment = p;
    _lines = (p['lines'] as List? ?? const []).cast<Map>().map((l) => l.cast<String, dynamic>()).toList();
    for (final l in _lines) {
      _amounts.add(TextEditingController(text: plainAmount('${l['amount']}')));
    }
    _mode = '${p['mode']}';
    _reference.text = '${p['reference_number'] ?? ''}';
    _notes.text = '${p['notes'] ?? ''}';
    return p;
  }

  static String plainAmount(String v) => v.endsWith('.00') ? v.substring(0, v.length - 3) : v;

  bool get _amountsChanged {
    for (var i = 0; i < _lines.length; i++) {
      if (double.tryParse(_amounts[i].text.trim()) != double.tryParse('${_lines[i]['amount']}')) return true;
    }
    return false;
  }

  Future<void> _save() async {
    final app = AppScope.read(context);
    final t = app.t;
    final p = _payment!;
    final money = RegExp(r'^\d+(\.\d{1,2})?$');
    for (final c in _amounts) {
      if (!money.hasMatch(c.text.trim())) {
        showMessage(context, t('edit_pavti_amount_invalid'), error: true);
        return;
      }
    }
    final body = <String, dynamic>{
      if (_mode != p['mode']) 'mode': _mode,
      if (_reference.text.trim() != '${p['reference_number'] ?? ''}') 'reference_number': _reference.text.trim(),
      if (_notes.text.trim() != '${p['notes'] ?? ''}') 'notes': _notes.text.trim(),
      if (_amountsChanged)
        'lines': [
          for (var i = 0; i < _lines.length; i++)
            {
              'contribution_type': _lines[i]['contribution_type'],
              'period_month': _lines[i]['period_month'],
              'amount': _amounts[i].text.trim(),
              if ('${_lines[i]['notes'] ?? ''}'.isNotEmpty) 'notes': _lines[i]['notes'],
            },
        ],
    };
    if (body.isEmpty) {
      Navigator.pop(context, false);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await app.api.post('/payments/${widget.paymentId}/edit/', body);
      if (!mounted) return;
      showMessage(context, t('saved'));
      Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e);
      showMessage(context, e.message, error: true);
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
          final modes = [
            for (final m in collectionModes)
              if (!app.modeHidden(m) || m == _mode) m,
          ];
          final total = _amounts.fold<double>(0, (s, c) => s + (double.tryParse(c.text.trim()) ?? 0));
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                t('edit_pavti_hint', {'number': widget.receiptNumber}),
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              Text('${p['payer_name'] ?? ''}', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              for (var i = 0; i < _lines.length; i++)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: TextField(
                    key: Key('edit-amount-$i'),
                    controller: _amounts[i],
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    onChanged: (_) => setState(() {}),
                    decoration: InputDecoration(
                      prefixText: '₹ ',
                      labelText: [
                        _lines[i]['contribution_type_name'],
                        if (_lines[i]['period_month'] != null) formatDate('${_lines[i]['period_month']}').substring(3),
                      ].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
                      errorText: _error?.fieldError('lines.$i.amount'),
                    ),
                  ),
                ),
              if (_error?.fieldError('lines') != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    _error!.fieldError('lines')!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                ),
              Row(
                children: [
                  Expanded(child: Text(t('total'), style: Theme.of(context).textTheme.titleSmall)),
                  Text(formatInr(total.toStringAsFixed(2)), style: Theme.of(context).textTheme.titleMedium),
                ],
              ),
              const SizedBox(height: 16),
              Text(t('payment_mode'), style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              if (_mode == 'online')
                Text(modeLabel(app, _mode))
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final m in modes)
                      ChoiceChip(
                        key: Key('edit-mode-$m'),
                        label: Text(modeLabel(app, m)),
                        selected: _mode == m,
                        onSelected: (_) => setState(() => _mode = m),
                      ),
                  ],
                ),
              const SizedBox(height: 16),
              if (_mode != 'cash')
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: TextField(
                    key: const Key('edit-reference'),
                    controller: _reference,
                    decoration: InputDecoration(
                      labelText: modesNeedingReference.contains(_mode) ? '${t('reference')} *' : t('reference'),
                      errorText: _error?.fieldError('reference_number'),
                    ),
                  ),
                ),
              TextField(
                key: const Key('edit-notes'),
                controller: _notes,
                maxLength: 500,
                decoration: InputDecoration(labelText: t('notes')),
              ),
              const SizedBox(height: 16),
              FilledButton(
                key: const Key('edit-save'),
                onPressed: _busy ? null : _save,
                child: Padding(padding: const EdgeInsets.all(12), child: Text(t('save'))),
              ),
            ],
          );
        },
      ),
    );
  }
}
