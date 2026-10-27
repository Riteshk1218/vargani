import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../state/app_state.dart';
import '../util/money.dart';

/// Gives every screen access to [AppState] and rebuilds on changes.
class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child}) : super(notifier: state);

  static AppState of(BuildContext context) => context.dependOnInheritedWidgetOfExactType<AppScope>()!.notifier!;

  static AppState read(BuildContext context) => context.getInheritedWidgetOfExactType<AppScope>()!.notifier!;
}

String errorText(BuildContext context, Object error) {
  if (error is ApiException) return error.message;
  return AppScope.read(context).t('offline');
}

void showMessage(BuildContext context, String text, {bool error = false}) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(text), backgroundColor: error ? Theme.of(context).colorScheme.error : null));
}

/// Loads data with [load], with loading, error-with-retry and pull-to-refresh states.
class AsyncView<T> extends StatefulWidget {
  const AsyncView({super.key, required this.load, required this.builder, this.reloadKey});

  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data, Future<void> Function() reload) builder;

  /// Reloads when this changes (for example the selected event).
  final Object? reloadKey;

  @override
  State<AsyncView<T>> createState() => _AsyncViewState<T>();
}

class _AsyncViewState<T> extends State<AsyncView<T>> {
  late Future<T> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.load();
  }

  @override
  void didUpdateWidget(covariant AsyncView<T> old) {
    super.didUpdateWidget(old);
    if (old.reloadKey != widget.reloadKey) _future = widget.load();
  }

  Future<void> _reload() async {
    final f = widget.load();
    setState(() => _future = f);
    await f.catchError((_) => null as T);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.cloud_off, size: 40, color: Theme.of(context).colorScheme.error),
                  const SizedBox(height: 12),
                  Text(errorText(context, snap.error!), textAlign: TextAlign.center),
                  const SizedBox(height: 12),
                  FilledButton.tonal(onPressed: _reload, child: Text(AppScope.read(context).t('retry'))),
                ],
              ),
            ),
          );
        }
        return RefreshIndicator(onRefresh: _reload, child: widget.builder(context, snap.data as T, _reload));
      },
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 80),
        Icon(icon, size: 48, color: Theme.of(context).colorScheme.outline),
        const SizedBox(height: 12),
        Text(text, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
      ],
    );
  }
}

class StatCard extends StatelessWidget {
  const StatCard({super.key, required this.label, required this.amount, this.highlight = false, this.onTap});
  final String label;
  final String? amount;
  final bool highlight;

  /// Opens the list behind the number.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      color: highlight ? scheme.primaryContainer : null,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: Text(label, style: Theme.of(context).textTheme.labelMedium)),
                  if (onTap != null) Icon(Icons.chevron_right, size: 18, color: scheme.outline),
                ],
              ),
              const SizedBox(height: 6),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  formatInr(amount),
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip(this.status, {super.key});
  final String status;

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final scheme = Theme.of(context).colorScheme;
    final ok = const {'issued', 'successful', 'approved'}.contains(status);
    final waiting = const {'submitted', 'draft', 'pending'}.contains(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: ok ? scheme.secondaryContainer : (waiting ? scheme.tertiaryContainer : scheme.errorContainer),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(switch (status) {
        'issued' => app.t('status_issued'),
        'void' || 'voided' => app.t('status_void'),
        'cancelled' => app.t('status_cancelled'),
        'draft' => app.t('status_draft'),
        'submitted' => app.t('status_submitted'),
        'approved' => app.t('status_approved'),
        'rejected' => app.t('status_rejected'),
        'deleted' => app.t('status_deleted'),
        'pending' => app.t('status_pending'),
        'failed' => app.t('status_failed'),
        'refunded' => app.t('status_refunded'),
        _ => status,
      }, style: Theme.of(context).textTheme.labelSmall),
    );
  }
}

String modeLabel(AppState app, String? mode) =>
    app.customModeLabel('$mode') ??
    switch (mode) {
      'cash' => app.t('cash'),
      'upi' => app.t('upi'),
      'bank_transfer' => app.t('bank_transfer'),
      'cheque' => app.t('cheque'),
      'online' || 'gateway' => app.t('online'),
      _ => app.t('other'),
    };

/// Event switcher shown in the app bar.
class EventSwitcher extends StatelessWidget {
  const EventSwitcher({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (app.events.isEmpty) return const SizedBox.shrink();
    return PopupMenuButton<String>(
      tooltip: app.t('choose_event'),
      onSelected: app.selectEvent,
      itemBuilder: (_) => [
        for (final e in app.events)
          CheckedPopupMenuItem(value: e['id'] as String, checked: e['id'] == app.eventId, child: Text('${e['name']}')),
      ],
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 150),
              child: Text(
                '${app.event?['name'] ?? ''}',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelLarge,
              ),
            ),
            const Icon(Icons.arrow_drop_down),
          ],
        ),
      ),
    );
  }
}
