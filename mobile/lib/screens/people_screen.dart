import 'dart:async';

import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../util/files.dart';
import '../widgets/common.dart';
import '../widgets/list_tools.dart';
import 'collect_screen.dart';
import 'person_screen.dart';

/// People the user may collect from. Collectors get only their assigned people;
/// the API decides that, not the app.
class PeopleScreen extends StatelessWidget {
  const PeopleScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    // With access to payments, a person opens their contribution history (Collect is one tap from there).
    final list = PersonSearchList(
      onPick: (p) => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => app.can('payments.view') ? PersonScreen(person: p) : CollectScreen(person: p),
        ),
      ),
    );
    if (!app.can('reports.export')) return list;
    return Column(
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: TextButton.icon(
              key: const Key('people-download'),
              onPressed: () => downloadPeople(context),
              icon: const Icon(Icons.download_outlined),
              label: Text(app.t('download_contacts')),
            ),
          ),
        ),
        Expanded(child: list),
      ],
    );
  }
}

/// Everyone's name, mobile, email and address as Excel or CSV, to send them updates. Opens in Sheets or
/// Excel on the phone, from where it can be shared or saved.
Future<void> downloadPeople(BuildContext context) async {
  final app = AppScope.read(context);
  final file = await showModalBottomSheet<String>(
    context: context,
    builder: (ctx) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(title: Text(app.t('download_contacts'), style: Theme.of(ctx).textTheme.titleMedium)),
          ListTile(
            leading: const Icon(Icons.table_chart_outlined),
            title: Text(app.t('download_excel')),
            onTap: () => Navigator.pop(ctx, 'xlsx'),
          ),
          ListTile(
            leading: const Icon(Icons.description_outlined),
            title: Text(app.t('download_csv')),
            onTap: () => Navigator.pop(ctx, 'csv'),
          ),
        ],
      ),
    ),
  );
  if (file == null) return;
  try {
    final bytes = await app.api.getBytes('/people/download/', query: {'file': file});
    await openFileBytes(
      bytes,
      'people.$file',
      file == 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    );
  } catch (e) {
    if (context.mounted) showMessage(context, errorText(context, e), error: true);
  }
}

class PersonSearchList extends StatefulWidget {
  const PersonSearchList({super.key, required this.onPick, this.searchFirst = false});
  final void Function(Map<String, dynamic> person) onPick;

  /// List nobody until something is typed (picking a contributor from hundreds of donors).
  final bool searchFirst;

  @override
  State<PersonSearchList> createState() => _PersonSearchListState();
}

class _PersonSearchListState extends State<PersonSearchList> {
  final _search = TextEditingController();
  Timer? _debounce;
  final List<Map<String, dynamic>> _items = [];
  int _page = 1;
  ListQuery _query = const ListQuery(ordering: 'full_name');
  bool _hasMore = false;
  bool _loading = false;
  Object? _error;

  @override
  void initState() {
    super.initState();
    if (!widget.searchFirst) _load(reset: true);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  /// A typed mobile number like "98678 50909" is stored as "+919867850909": drop spaces and dashes.
  String get _term {
    final text = _search.text.trim();
    return RegExp(r'^[+\d\s-]+$').hasMatch(text) ? text.replaceAll(RegExp(r'[\s-]'), '') : text;
  }

  bool get _waitingForSearch => widget.searchFirst && _term.isEmpty;

  Future<void> _load({bool reset = false}) async {
    if (reset) {
      _page = 1;
    }
    if (_waitingForSearch) {
      setState(() {
        _items.clear();
        _hasMore = false;
        _error = null;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await AppScope.read(context).api
          .get('/people/', query: {'search': _term, 'page': '$_page', if (!widget.searchFirst) ..._query.query});
      if (!mounted) return;
      setState(() {
        if (reset) _items.clear();
        _items.addAll(resultsOf(data));
        _hasMore = data is Map && data['next'] != null;
        _page += 1;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: TextField(
            key: const Key('people-search'),
            controller: _search,
            autofocus: widget.searchFirst,
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search),
              hintText: app.t('search_people'),
              border: const OutlineInputBorder(),
              isDense: true,
            ),
            onChanged: (_) {
              _debounce?.cancel();
              _debounce = Timer(const Duration(milliseconds: 350), () => _load(reset: true));
            },
          ),
        ),
        if (!widget.searchFirst)
          ListToolsBar(
            value: _query,
            onChanged: (q) {
              setState(() => _query = q);
              _load(reset: true);
            },
            sortOptions: const [
              SortOption('full_name', 'list_name'),
              SortOption('created_at', 'list_created_at'),
              SortOption('area', 'list_area'),
            ],
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () => _load(reset: true),
            child: _error != null && _items.isEmpty
                ? ListView(
                    children: [
                      const SizedBox(height: 60),
                      Text(errorText(context, _error!), textAlign: TextAlign.center),
                      Center(
                        child: TextButton(onPressed: () => _load(reset: true), child: Text(app.t('retry'))),
                      ),
                    ],
                  )
                : _waitingForSearch
                ? EmptyState(icon: Icons.search, text: app.t('search_people'))
                : _items.isEmpty && !_loading
                ? EmptyState(icon: Icons.person_search, text: app.t('no_people'))
                : ListView.builder(
                    padding: const EdgeInsets.only(bottom: 96),
                    itemCount: _items.length + 1,
                    itemBuilder: (context, i) {
                      if (i == _items.length) {
                        if (_loading) {
                          return const Padding(
                            padding: EdgeInsets.all(16),
                            child: Center(child: CircularProgressIndicator()),
                          );
                        }
                        return _hasMore
                            ? Center(
                                child: TextButton(onPressed: _load, child: const Icon(Icons.expand_more)),
                              )
                            : const SizedBox.shrink();
                      }
                      final p = _items[i];
                      final sub = [
                        p['mobile'],
                        p['unit'],
                        p['building'],
                        p['area'],
                      ].where((s) => s != null && '$s'.isNotEmpty).join(' · ');
                      return ListTile(
                        leading: CircleAvatar(child: Text('${p['full_name']}'.characters.first)),
                        title: Text('${p['full_name']}'),
                        subtitle: widget.searchFirst
                            ? (sub.isEmpty ? null : Text(sub))
                            : Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [if (sub.isNotEmpty) Text(sub), CreatedLine(p)],
                              ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => widget.onPick(p),
                      );
                    },
                  ),
          ),
        ),
      ],
    );
  }
}
