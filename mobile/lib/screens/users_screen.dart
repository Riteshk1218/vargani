import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/api_client.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';

/// Role names in the app's language for the built-in roles; an organization's own roles keep their name.
String roleLabel(AppState app, Map? role) {
  final code = role?['code']?.toString() ?? '';
  final label = app.t('role_$code');
  return label == 'role_$code' ? '${role?['name'] ?? ''}' : label;
}

/// What the person types in the login box: their username, else mobile, else email.
String loginOf(Map user) => '${user['username'] ?? user['mobile'] ?? user['email'] ?? ''}';

/// An easy-to-read password the admin can share, e.g. "Kmrt-4829-Pqws" (same shape as the website's).
String generatePassword() {
  const letters = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ';
  const digits = '23456789';
  final rnd = Random.secure();
  String pick(String chars, int n) => List.generate(n, (_) => chars[rnd.nextInt(chars.length)]).join();
  return '${pick(letters, 4)}-${pick(digits, 4)}-${pick(letters, 4)}';
}

/// Organization admins add logins for collectors and others, change their role, deactivate,
/// set a new password or delete them. The API checks `members.manage` on every call.
class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});
  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  int _reload = 0;
  List<Map<String, dynamic>> _roles = const [];

  Future<List<Map<String, dynamic>>> _load() async {
    final api = AppScope.read(context).api;
    final results = await Future.wait([
      api.get('/members/', query: {'page_size': '100'}),
      api.get('/roles/'),
    ]);
    _roles = resultsOf(results[1]);
    return resultsOf(results[0]);
  }

  void _refresh() => setState(() => _reload++);

  Future<void> _run(Future<void> Function() action, [String? done]) async {
    final app = AppScope.read(context);
    try {
      await action();
      if (mounted) showMessage(context, done ?? app.t('saved'));
      _refresh();
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    }
  }

  Future<void> _actions(Map<String, dynamic> member) async {
    final app = AppScope.read(context);
    final user = (member['user'] as Map).cast<String, dynamic>();
    final active = member['status'] == 'active';
    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: Text('${user['full_name']}', style: Theme.of(ctx).textTheme.titleMedium),
              subtitle: Text(loginOf(user)),
            ),
            ListTile(
              key: const Key('user-role'),
              leading: const Icon(Icons.badge_outlined),
              title: Text(app.t('change_role')),
              onTap: () => Navigator.pop(ctx, 'role'),
            ),
            ListTile(
              key: const Key('user-status'),
              leading: Icon(active ? Icons.block : Icons.check_circle_outline),
              title: Text(active ? app.t('deactivate') : app.t('activate')),
              onTap: () => Navigator.pop(ctx, 'status'),
            ),
            if (member['can_reset_password'] == true)
              ListTile(
                key: const Key('user-password'),
                leading: const Icon(Icons.key_outlined),
                title: Text(app.t('set_password')),
                onTap: () => Navigator.pop(ctx, 'password'),
              ),
            ListTile(
              key: const Key('user-delete'),
              leading: Icon(Icons.delete_outline, color: Theme.of(ctx).colorScheme.error),
              title: Text(app.t('delete'), style: TextStyle(color: Theme.of(ctx).colorScheme.error)),
              onTap: () => Navigator.pop(ctx, 'delete'),
            ),
          ],
        ),
      ),
    );
    if (!mounted || choice == null) return;
    final id = member['id'];
    switch (choice) {
      case 'role':
        final roleId = await _pickRole((member['role'] as Map?)?['id']?.toString());
        if (roleId != null) await _run(() => app.api.patch('/members/$id/', {'role_id': roleId}));
      case 'status':
        await _run(() => app.api.patch('/members/$id/', {'status': active ? 'suspended' : 'active'}));
      case 'password':
        await _setPassword(member);
      case 'delete':
        final ok = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: Text(app.t('delete_user_title', {'name': '${user['full_name']}'})),
            content: Text(app.t('delete_user_body')),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(app.t('cancel'))),
              FilledButton(
                key: const Key('confirm-delete'),
                style: FilledButton.styleFrom(backgroundColor: Theme.of(ctx).colorScheme.error),
                onPressed: () => Navigator.pop(ctx, true),
                child: Text(app.t('delete')),
              ),
            ],
          ),
        );
        if (ok == true) await _run(() => app.api.post('/members/$id/remove/'), app.t('user_deleted'));
    }
  }

  Future<String?> _pickRole(String? current) {
    final app = AppScope.read(context);
    return showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: Text(app.t('change_role')),
        children: [
          RadioGroup<String>(
            groupValue: current,
            onChanged: (v) => Navigator.pop(ctx, v),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final r in _roles) RadioListTile<String>(value: '${r['id']}', title: Text(roleLabel(app, r))),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _setPassword(Map<String, dynamic> member) async {
    final app = AppScope.read(context);
    final user = (member['user'] as Map).cast<String, dynamic>();
    final password = await showDialog<String>(
      context: context,
      builder: (ctx) => _PasswordDialog(title: app.t('set_password')),
    );
    if (password == null || !mounted) return;
    try {
      await app.api.post('/members/${member['id']}/set-password/', {'password': password});
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => _LoginDetailsDialog(
          intro: app.t('password_set'),
          name: '${user['full_name']}',
          login: loginOf(user),
          mobile: user['mobile'] as String?,
          password: password,
        ),
      );
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final myId = app.user?['id'];
    return Scaffold(
      appBar: AppBar(title: Text(app.t('users'))),
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('fab-add-user'),
        icon: const Icon(Icons.person_add_alt),
        label: Text(app.t('add_user')),
        onPressed: () async {
          if (_roles.isEmpty) return;
          final added = await Navigator.push<bool>(
            context,
            MaterialPageRoute(builder: (_) => AddUserScreen(roles: _roles)),
          );
          if (added == true) _refresh();
        },
      ),
      body: AsyncView<List<Map<String, dynamic>>>(
        reloadKey: _reload,
        load: _load,
        builder: (context, members, reload) => ListView.separated(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.only(bottom: 88),
          itemCount: members.length,
          separatorBuilder: (_, _) => const Divider(height: 1),
          itemBuilder: (context, i) {
            final m = members[i];
            final user = (m['user'] as Map).cast<String, dynamic>();
            final self = user['id'] == myId;
            final active = m['status'] == 'active';
            return ListTile(
              key: Key('user-${m['id']}'),
              leading: CircleAvatar(child: Text('${user['full_name']}'.characters.firstOrNull ?? '?')),
              title: Text(self ? '${user['full_name']} (${app.t('you')})' : '${user['full_name']}'),
              subtitle: Text('${loginOf(user)} · ${roleLabel(app, m['role'] as Map?)}'),
              trailing: active ? null : Chip(label: Text(app.t('inactive')), visualDensity: VisualDensity.compact),
              onTap: self ? null : () => _actions(m),
            );
          },
        ),
      ),
    );
  }
}

class _PasswordDialog extends StatefulWidget {
  const _PasswordDialog({required this.title});
  final String title;
  @override
  State<_PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<_PasswordDialog> {
  final _ctrl = TextEditingController(text: generatePassword());

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return AlertDialog(
      title: Text(widget.title),
      content: _PasswordField(controller: _ctrl),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(app.t('cancel'))),
        FilledButton(
          onPressed: () {
            if (_ctrl.text.isNotEmpty) Navigator.pop(context, _ctrl.text);
          },
          child: Text(app.t('save')),
        ),
      ],
    );
  }
}

/// Password box that stays readable so the admin can copy it, with a "Make a password" button.
class _PasswordField extends StatelessWidget {
  const _PasswordField({required this.controller, this.errorText});
  final TextEditingController controller;
  final String? errorText;

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          key: const Key('user-password-field'),
          controller: controller,
          autocorrect: false,
          enableSuggestions: false,
          decoration: InputDecoration(
            labelText: app.t('password'),
            helperText: app.t('password_hint'),
            errorText: errorText,
            border: const OutlineInputBorder(),
          ),
          validator: (v) => (v == null || v.isEmpty) ? app.t('required') : null,
        ),
        TextButton.icon(
          icon: const Icon(Icons.key_outlined),
          label: Text(app.t('make_password')),
          onPressed: () => controller.text = generatePassword(),
        ),
      ],
    );
  }
}

class _LoginDetailsDialog extends StatelessWidget {
  const _LoginDetailsDialog({
    required this.intro,
    required this.name,
    required this.login,
    required this.password,
    this.mobile,
  });
  final String intro;
  final String name;
  final String login;
  final String password;
  final String? mobile;

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final message = app.t('login_message', {
      'name': name,
      'org': app.orgName,
      'site': app.api.baseUrl,
      'login': login,
      'password': password,
    });
    return AlertDialog(
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(intro),
          const SizedBox(height: 12),
          SelectableText(
            '${app.t('login_label')}: $login\n${app.t('password')}: $password',
            style: const TextStyle(fontFamily: 'monospace'),
          ),
          const SizedBox(height: 12),
          Text(app.t('login_once'), style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: message));
            if (context.mounted) showMessage(context, app.t('copied'));
          },
          child: Text(app.t('copy_details')),
        ),
        TextButton(
          onPressed: () => launchUrl(
            Uri.parse('https://wa.me/${(mobile ?? '').replaceAll(RegExp(r'\D'), '')}')
                .replace(queryParameters: {'text': message}),
            mode: LaunchMode.externalApplication,
          ),
          child: Text(app.t('share_whatsapp')),
        ),
        FilledButton(onPressed: () => Navigator.pop(context), child: Text(app.t('close'))),
      ],
    );
  }
}

class AddUserScreen extends StatefulWidget {
  const AddUserScreen({super.key, required this.roles});
  final List<Map<String, dynamic>> roles;
  @override
  State<AddUserScreen> createState() => _AddUserScreenState();
}

class _AddUserScreenState extends State<AddUserScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _username = TextEditingController();
  final _mobile = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController(text: generatePassword());
  String? _roleId;
  bool _busy = false;
  ApiException? _error;

  @override
  void initState() {
    super.initState();
    final collector = widget.roles.where((r) => r['code'] == 'collector');
    _roleId = (collector.isNotEmpty ? collector.first['id'] : null)?.toString();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    final app = AppScope.read(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    String? opt(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();
    try {
      final res = (await app.api.post('/members/', {
        'full_name': _name.text.trim(),
        'username': opt(_username),
        'mobile': opt(_mobile),
        'email': opt(_email),
        'password': _password.text,
        'role_id': _roleId,
      }) as Map).cast<String, dynamic>();
      if (!mounted) return;
      setState(() => _busy = false);
      final user = (res['user'] as Map).cast<String, dynamic>();
      final name = '${user['full_name']}';
      if (res['new_login'] == false) {
        await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
            content: Text(app.t('user_existing', {'name': name})),
            actions: [FilledButton(onPressed: () => Navigator.pop(ctx), child: Text(app.t('close')))],
          ),
        );
      } else {
        await showDialog<void>(
          context: context,
          builder: (ctx) => _LoginDetailsDialog(
            intro: app.t('user_added', {'name': name}),
            name: name,
            login: loginOf(user),
            mobile: user['mobile'] as String?,
            password: _password.text,
          ),
        );
      }
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e);
      final general = e.fieldError('non_field_errors') ?? (e.details.isEmpty ? e.message : null);
      if (general != null) showMessage(context, general, error: true);
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    InputDecoration deco(String label, String field, {String? helper}) => InputDecoration(
      labelText: label,
      helperText: helper,
      helperMaxLines: 3,
      errorText: _error?.fieldError(field),
      border: const OutlineInputBorder(),
    );
    return Scaffold(
      appBar: AppBar(title: Text(app.t('add_user'))),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              key: const Key('add-user-name'),
              controller: _name,
              textCapitalization: TextCapitalization.words,
              decoration: deco(app.t('full_name'), 'full_name'),
              validator: (v) => (v == null || v.trim().isEmpty) ? app.t('required') : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              key: const Key('add-user-username'),
              controller: _username,
              autocorrect: false,
              enableSuggestions: false,
              decoration: deco(app.t('username'), 'username', helper: app.t('username_hint')),
            ),
            const SizedBox(height: 16),
            TextFormField(
              key: const Key('add-user-mobile'),
              controller: _mobile,
              keyboardType: TextInputType.phone,
              decoration: deco('${app.t('mobile')} (${app.t('optional')})', 'mobile'),
            ),
            const SizedBox(height: 16),
            TextFormField(
              key: const Key('add-user-email'),
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: deco('${app.t('email')} (${app.t('optional')})', 'email'),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(app.t('login_hint'), style: Theme.of(context).textTheme.bodySmall),
            ),
            const SizedBox(height: 8),
            _PasswordField(controller: _password, errorText: _error?.fieldError('password')),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              key: const Key('add-user-role'),
              initialValue: _roleId,
              decoration: deco(app.t('role'), 'role_id'),
              items: [
                for (final r in widget.roles) DropdownMenuItem(value: '${r['id']}', child: Text(roleLabel(app, r))),
              ],
              onChanged: (v) => setState(() => _roleId = v),
              validator: (v) => v == null ? app.t('required') : null,
            ),
            const SizedBox(height: 24),
            FilledButton(
              key: const Key('add-user-save'),
              onPressed: _busy ? null : _submit,
              child: _busy
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(app.t('add_user')),
            ),
          ],
        ),
      ),
    );
  }
}
