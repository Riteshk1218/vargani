import 'package:flutter/material.dart';

import '../l10n/strings.dart';
import '../widgets/common.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(app.t('app_name')),
          actions: const [LanguageMenu(), _ServerButton()],
          bottom: TabBar(tabs: [Tab(text: app.t('committee')), Tab(text: app.t('member'))]),
        ),
        body: const TabBarView(children: [_PasswordLogin(), _OtpLogin()]),
      ),
    );
  }
}

class LanguageMenu extends StatelessWidget {
  const LanguageMenu({super.key});

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return PopupMenuButton<String>(
      key: const Key('language-menu'),
      icon: const Icon(Icons.translate),
      tooltip: app.t('language'),
      onSelected: app.setLanguage,
      itemBuilder: (_) => [
        for (final e in supportedLanguages.entries)
          CheckedPopupMenuItem(value: e.key, checked: e.key == app.language, child: Text(e.value)),
      ],
    );
  }
}

class _ServerButton extends StatelessWidget {
  const _ServerButton();

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return IconButton(
      icon: const Icon(Icons.dns_outlined),
      tooltip: app.t('server'),
      onPressed: () async {
        final ctrl = TextEditingController(text: app.api.baseUrl);
        final url = await showDialog<String>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: Text(app.t('server')),
            content: TextField(
              controller: ctrl,
              keyboardType: TextInputType.url,
              decoration: InputDecoration(hintText: app.t('server_hint')),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: Text(app.t('cancel'))),
              FilledButton(onPressed: () => Navigator.pop(ctx, ctrl.text), child: Text(app.t('save'))),
            ],
          ),
        );
        if (url != null && url.trim().isNotEmpty) await app.setApiBase(url);
      },
    );
  }
}

class _Logo extends StatelessWidget {
  const _Logo();
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 24),
        child: Icon(Icons.volunteer_activism, size: 64, color: Theme.of(context).colorScheme.primary),
      );
}

class _PasswordLogin extends StatefulWidget {
  const _PasswordLogin();
  @override
  State<_PasswordLogin> createState() => _PasswordLoginState();
}

class _PasswordLoginState extends State<_PasswordLogin> {
  final _form = GlobalKey<FormState>();
  final _id = TextEditingController();
  final _pw = TextEditingController();
  bool _busy = false;
  bool _hide = true;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await AppScope.read(context).loginWithPassword(_id.text, _pw.text);
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? app.t('required') : null;
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Form(
            key: _form,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const _Logo(),
              TextFormField(
                key: const Key('login-identifier'),
                controller: _id,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.username],
                decoration: InputDecoration(labelText: app.t('email_or_mobile'), border: const OutlineInputBorder()),
                validator: req,
              ),
              const SizedBox(height: 16),
              TextFormField(
                key: const Key('login-password'),
                controller: _pw,
                obscureText: _hide,
                autofillHints: const [AutofillHints.password],
                decoration: InputDecoration(
                  labelText: app.t('password'),
                  border: const OutlineInputBorder(),
                  suffixIcon: IconButton(
                    icon: Icon(_hide ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _hide = !_hide),
                  ),
                ),
                validator: req,
                onFieldSubmitted: (_) => _submit(),
              ),
              const SizedBox(height: 24),
              FilledButton(
                key: const Key('login-submit'),
                onPressed: _busy ? null : _submit,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: _busy
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : Text(app.t('login')),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _OtpLogin extends StatefulWidget {
  const _OtpLogin();
  @override
  State<_OtpLogin> createState() => _OtpLoginState();
}

class _OtpLoginState extends State<_OtpLogin> {
  final _mobile = TextEditingController();
  final _code = TextEditingController();
  String? _sentTo;
  bool _busy = false;

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } catch (e) {
      if (mounted) showMessage(context, errorText(context, e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _send() => _run(() async {
        if (_mobile.text.trim().isEmpty) return;
        final r = await AppScope.read(context).requestOtp(_mobile.text);
        setState(() => _sentTo = (r['verification'] as Map?)?['destination']?.toString() ?? _mobile.text);
        // Development servers echo the code so the flow can be tested without SMS.
        final debug = r['debug_code']?.toString();
        if (debug != null) _code.text = debug;
      });

  void _verify() => _run(() => AppScope.read(context).verifyOtp(_mobile.text, _code.text));

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const _Logo(),
            TextField(
              key: const Key('otp-mobile'),
              controller: _mobile,
              keyboardType: TextInputType.phone,
              enabled: _sentTo == null,
              decoration: InputDecoration(
                  labelText: app.t('mobile'), prefixText: '+91 ', border: const OutlineInputBorder()),
            ),
            const SizedBox(height: 16),
            if (_sentTo == null)
              FilledButton(
                key: const Key('otp-send'),
                onPressed: _busy ? null : _send,
                child: Padding(padding: const EdgeInsets.all(12), child: Text(app.t('send_code'))),
              )
            else ...[
              Text(app.t('code_sent', {'dest': _sentTo!}), textAlign: TextAlign.center),
              const SizedBox(height: 12),
              TextField(
                key: const Key('otp-code'),
                controller: _code,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                decoration: InputDecoration(labelText: app.t('code'), border: const OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              FilledButton(
                key: const Key('otp-verify'),
                onPressed: _busy ? null : _verify,
                child: Padding(padding: const EdgeInsets.all(12), child: Text(app.t('verify'))),
              ),
              TextButton(
                onPressed: _busy ? null : () => setState(() => _sentTo = null),
                child: Text(app.t('cancel')),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}
