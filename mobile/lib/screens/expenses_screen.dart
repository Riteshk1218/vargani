import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api/api_client.dart';
import '../util/money.dart';
import '../widgets/bulk_delete.dart';
import '../widgets/common.dart';
import '../widgets/list_tools.dart';
import 'collect_screen.dart' show collectionModes;

/// Expenses in the current event. Collectors see the ones they entered; approvers see all and can
/// approve or reject. Only approved expenses count in the balance.
class ExpensesScreen extends StatefulWidget {
  const ExpensesScreen({super.key, this.dateFrom, this.dateTo, this.status});

  /// Opened from the dashboard for one day: those days, and only approved expenses (what the balance counts).
  final String? dateFrom;
  final String? dateTo;
  final String? status;

  @override
  State<ExpensesScreen> createState() => _ExpensesScreenState();
}

class _ExpensesScreenState extends State<ExpensesScreen> with BulkSelect {
  int _version = 0;
  late ListQuery _query = ListQuery(dateFrom: widget.dateFrom, dateTo: widget.dateTo, ordering: '-expense_date');

  void _refresh() => setState(() => _version++);

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (app.eventId == null) return EmptyState(icon: Icons.event_busy, text: app.t('no_events'));
    return Scaffold(
      body: Column(
        children: [
          ListToolsBar(
            value: _query,
            onChanged: (q) => setState(() => _query = q),
            sortOptions: const [
              SortOption('expense_date', 'list_date'),
              SortOption('created_at', 'list_created_at'),
              SortOption('amount', 'list_amount'),
              SortOption('payee', 'list_paid_to'),
            ],
          ),
          if (selecting)
            BulkDeleteBar(
              count: selected.length,
              onSelectAll: toggleAllVisible,
              onClear: clearSelected,
              onDelete: () => confirmBulkDelete('/expenses/'),
            ),
          Expanded(
            child: AsyncView<List<Map<String, dynamic>>>(
              reloadKey: '${app.eventId}-$_version-${_query.key}-$bulkVersion',
              load: () async => resultsOf(
                await app.api.get(
                  '/expenses/',
                  query: {
                    'event': app.eventId,
                    if (widget.status != null) 'status': widget.status,
                    ..._query.query,
                    'page_size': '100',
                  },
                ),
              ),
              builder: (context, items, reload) {
                visibleIds = [for (final e in items) '${e['id']}'];
                return items.isEmpty
                  ? EmptyState(icon: Icons.receipt_outlined, text: app.t('no_expenses'))
                  : ListView.separated(
                      padding: const EdgeInsets.only(bottom: 96),
                      itemCount: items.length,
                      separatorBuilder: (_, _) => const Divider(height: 1),
                      itemBuilder: (context, i) {
                        final e = items[i];
                        final id = '${e['id']}';
                        return ListTile(
                          key: Key('expense-$id'),
                          leading: selectBox(id),
                          onLongPress: app.can(deletePermission) ? () => toggleSelected(id) : null,
                          title: Text(expenseTitle(e), overflow: TextOverflow.ellipsis),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [Text('${expenseWhen(e)} · ${e['category_name']}'), CreatedLine(e)],
                          ),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text(formatInr('${e['amount']}'), style: Theme.of(context).textTheme.titleSmall),
                              StatusChip('${e['status']}'),
                            ],
                          ),
                          onTap: selecting
                              ? () => toggleSelected(id)
                              : () => Navigator.push(
                                  context,
                                  MaterialPageRoute(builder: (_) => ExpenseDetailScreen(expenseId: id)),
                                ).then((_) => reload()),
                        );
                      },
                    );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: app.can('expenses.create') && widget.status == null
          ? FloatingActionButton.extended(
              key: const Key('fab-expense'),
              icon: const Icon(Icons.add),
              label: Text(app.t('add_expense')),
              onPressed: () async {
                final added = await Navigator.push<bool>(
                  context,
                  MaterialPageRoute(builder: (_) => const AddExpenseScreen()),
                );
                if (added == true) _refresh();
              },
            )
          : null,
    );
  }
}

String expenseTitle(Map e) {
  final payee = '${e['payee'] ?? ''}';
  final description = '${e['description'] ?? ''}'.split('\n').first;
  return payee.isNotEmpty ? payee : (description.isNotEmpty ? description : '${e['category_name'] ?? ''}');
}

String expenseWhen(Map e) {
  final time = e['expense_time'];
  if (time == null) return formatDate('${e['expense_date']}');
  return formatStamp(DateTime.parse('${e['expense_date']}T$time').toUtc().toIso8601String());
}

/// Add an expense: category, purpose, amount, date and time (now by default), payment mode and an
/// optional bill photo, then send it for approval.
class AddExpenseScreen extends StatefulWidget {
  const AddExpenseScreen({super.key});

  @override
  State<AddExpenseScreen> createState() => _AddExpenseScreenState();
}

class _AddExpenseScreenState extends State<AddExpenseScreen> {
  List<Map<String, dynamic>>? _categories;
  Object? _loadError;
  String? _category;
  final _description = TextEditingController();
  final _amount = TextEditingController();
  final _payee = TextEditingController();
  final _reference = TextEditingController();
  String _mode = 'cash';
  DateTime _when = DateTime.now();
  XFile? _photo;
  bool _saving = false;
  ApiException? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await AppScope.read(context).api.get('/expense-categories/', query: {'is_active': 'true'});
      setState(() {
        _categories = resultsOf(data);
        _loadError = null;
      });
    } catch (e) {
      setState(() => _loadError = e);
    }
  }

  Future<void> _pickPhoto(ImageSource source) async {
    try {
      final photo = await ImagePicker().pickImage(source: source, maxWidth: 2000, imageQuality: 80);
      if (photo != null) setState(() => _photo = photo);
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    }
  }

  Future<void> _pickDateTime() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _when,
      firstDate: DateTime(_when.year - 2),
      lastDate: DateTime.now(),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_when));
    setState(
      () => _when = DateTime(date.year, date.month, date.day, time?.hour ?? _when.hour, time?.minute ?? _when.minute),
    );
  }

  Future<void> _save({required bool submit}) async {
    final app = AppScope.read(context);
    final t = app.t;
    final amount = normaliseAmount(_amount.text);
    if (_category == null) {
      showMessage(context, t('choose_category'), error: true);
      return;
    }
    if (amount == null) {
      showMessage(context, t('invalid_amount'), error: true);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      String two(int n) => n.toString().padLeft(2, '0');
      final created = (await app.api.post('/expenses/', {
        'event': app.eventId,
        'category': _category,
        'amount': amount,
        'description': _description.text.trim(),
        'payee': _payee.text.trim(),
        'reference_number': _reference.text.trim(),
        'mode': _mode,
        'expense_date': '${_when.year}-${two(_when.month)}-${two(_when.day)}',
        'expense_time': '${two(_when.hour)}:${two(_when.minute)}',
      })) as Map;
      final id = '${created['id']}';
      if (_photo != null) {
        await app.api.upload('/expenses/$id/attachments/', await _photo!.readAsBytes(), _photo!.name);
      }
      if (submit) await app.api.post('/expenses/$id/submit/');
      if (!mounted) return;
      showMessage(context, submit ? t('expense_submitted') : t('saved'));
      Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() => _error = e);
      showMessage(context, e.message, error: true);
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    final when = formatStamp(_when.toUtc().toIso8601String());
    return Scaffold(
      appBar: AppBar(title: Text(t('add_expense'))),
      body: _categories == null
          ? Center(
              child: _loadError == null
                  ? const CircularProgressIndicator()
                  : TextButton(onPressed: _load, child: Text(t('retry'))),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                DropdownButtonFormField<String>(
                  key: const Key('expense-category'),
                  initialValue: _category,
                  isExpanded: true,
                  decoration: InputDecoration(
                    labelText: t('category'),
                    errorText: _error?.fieldError('category'),
                    border: const OutlineInputBorder(),
                  ),
                  items: [
                    for (final c in _categories!) DropdownMenuItem(value: '${c['id']}', child: Text('${c['name']}')),
                  ],
                  onChanged: (v) => setState(() => _category = v),
                ),
                const SizedBox(height: 12),
                TextField(
                  key: const Key('expense-description'),
                  controller: _description,
                  maxLines: 2,
                  decoration: InputDecoration(
                    labelText: t('purpose'),
                    errorText: _error?.fieldError('description'),
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  key: const Key('expense-amount'),
                  controller: _amount,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(
                    labelText: t('amount'),
                    prefixText: '₹ ',
                    errorText: _error?.fieldError('amount'),
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _payee,
                  decoration: InputDecoration(
                    labelText: '${t('paid_to')} (${t('optional')})',
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 4),
                ListTile(
                  key: const Key('expense-when'),
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.schedule),
                  title: Text(t('date_time')),
                  subtitle: Text(_error?.fieldError('expense_date') ?? when),
                  trailing: const Icon(Icons.edit_calendar_outlined),
                  onTap: _pickDateTime,
                ),
                Text(t('payment_mode'), style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final m in collectionModes)
                      ChoiceChip(
                        label: Text(modeLabel(app, m)),
                        selected: _mode == m,
                        onSelected: (_) => setState(() => _mode = m),
                      ),
                  ],
                ),
                if (_mode != 'cash') ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: _reference,
                    decoration: InputDecoration(
                      labelText: '${t('reference')} (${t('optional')})',
                      border: const OutlineInputBorder(),
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                Text('${t('bill_photo')} (${t('optional')})', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                if (_photo != null)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.image_outlined),
                    title: Text(_photo!.name, overflow: TextOverflow.ellipsis),
                    trailing: IconButton(icon: const Icon(Icons.close), onPressed: () => setState(() => _photo = null)),
                  ),
                Wrap(
                  spacing: 8,
                  children: [
                    OutlinedButton.icon(
                      key: const Key('expense-camera'),
                      icon: const Icon(Icons.photo_camera_outlined),
                      label: Text(t('take_photo')),
                      onPressed: () => _pickPhoto(ImageSource.camera),
                    ),
                    OutlinedButton.icon(
                      icon: const Icon(Icons.photo_library_outlined),
                      label: Text(t('choose_photo')),
                      onPressed: () => _pickPhoto(ImageSource.gallery),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  key: const Key('expense-submit'),
                  onPressed: _saving ? null : () => _save(submit: true),
                  icon: _saving
                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send),
                  label: Padding(padding: const EdgeInsets.all(12), child: Text(t('submit_for_approval'))),
                ),
                const SizedBox(height: 8),
                TextButton(onPressed: _saving ? null : () => _save(submit: false), child: Text(t('save_draft'))),
              ],
            ),
    );
  }
}

/// One expense with its bills. The owner sends a draft for approval; an approver approves or rejects
/// with a reason; an Organization Admin can delete it.
class ExpenseDetailScreen extends StatefulWidget {
  const ExpenseDetailScreen({super.key, required this.expenseId});
  final String expenseId;

  @override
  State<ExpenseDetailScreen> createState() => _ExpenseDetailScreenState();
}

class _ExpenseDetailScreenState extends State<ExpenseDetailScreen> {
  int _version = 0;
  bool _busy = false;

  Future<void> _act(String action, {String? reason}) async {
    final app = AppScope.read(context);
    setState(() => _busy = true);
    try {
      if (action == 'delete') {
        await app.api.delete('/expenses/${widget.expenseId}/');
        if (mounted) Navigator.pop(context);
        return;
      }
      await app.api.post('/expenses/${widget.expenseId}/$action/', {'reason': ?reason});
      setState(() => _version++);
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reject() async {
    final t = AppScope.read(context).t;
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(t('reject')),
        content: TextField(
          key: const Key('reject-reason'),
          controller: reason,
          autofocus: true,
          decoration: InputDecoration(labelText: t('reason')),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(t('cancel'))),
          FilledButton(onPressed: () => Navigator.pop(ctx, reason.text.trim().isNotEmpty), child: Text(t('reject'))),
        ],
      ),
    );
    if (ok == true) await _act('reject', reason: reason.text.trim());
  }

  Future<void> _delete() async {
    final t = AppScope.read(context).t;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(t('delete_expense_confirm')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(t('cancel'))),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(t('delete'))),
        ],
      ),
    );
    if (ok == true) await _act('delete');
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final t = app.t;
    return Scaffold(
      appBar: AppBar(title: Text(t('expense'))),
      body: AsyncView<Map<String, dynamic>>(
        reloadKey: _version,
        load: () async => ((await app.api.get('/expenses/${widget.expenseId}/')) as Map).cast<String, dynamic>(),
        builder: (context, e, _) {
          final text = Theme.of(context).textTheme;
          final status = '${e['status']}';
          final bills = (e['attachments'] as List? ?? []).cast<Map>();
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
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(child: Text(formatInr('${e['amount']}'), style: text.headlineSmall)),
                          StatusChip(status),
                        ],
                      ),
                      if (status == 'rejected' && '${e['rejection_reason'] ?? ''}'.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            t('rejected_because', {'reason': '${e['rejection_reason']}'}),
                            style: TextStyle(color: Theme.of(context).colorScheme.error),
                          ),
                        ),
                      const Divider(height: 24),
                      row(t('category'), e['category_name']),
                      row(t('purpose'), e['description']),
                      row(t('paid_to'), e['payee']),
                      row(t('date_time'), expenseWhen(e)),
                      row(t('payment_mode'), modeLabel(app, '${e['mode']}')),
                      row(t('reference'), e['reference_number']),
                      row(t('entered_by'), e['created_by_name']),
                      row(t('approved_by'), status == 'approved' ? e['decided_by_name'] : null),
                      row(t('bill_photo'), bills.isEmpty ? t('none') : bills.map((b) => b['original_name']).join(', ')),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (app.can('expenses.create') && (status == 'draft' || status == 'rejected'))
                FilledButton.icon(
                  key: const Key('expense-send'),
                  onPressed: _busy ? null : () => _act('submit'),
                  icon: const Icon(Icons.send),
                  label: Padding(padding: const EdgeInsets.all(12), child: Text(t('submit_for_approval'))),
                ),
              if (app.can('expenses.approve') && status == 'submitted') ...[
                FilledButton.icon(
                  key: const Key('expense-approve'),
                  onPressed: _busy ? null : () => _act('approve'),
                  icon: const Icon(Icons.check),
                  label: Padding(padding: const EdgeInsets.all(12), child: Text(t('approve'))),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  key: const Key('expense-reject'),
                  onPressed: _busy ? null : _reject,
                  icon: const Icon(Icons.close),
                  label: Padding(padding: const EdgeInsets.all(12), child: Text(t('reject'))),
                ),
              ],
              if (app.can('records.admin_edit')) ...[
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: _busy ? null : _delete,
                  icon: const Icon(Icons.delete_outline),
                  label: Text(t('delete')),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
