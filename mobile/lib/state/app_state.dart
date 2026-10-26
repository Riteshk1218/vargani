import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../l10n/strings.dart';

/// Default API address, set at build time:
/// flutter build apk --dart-define=API_BASE=https://api.your-domain.in
/// Built for the web with `--dart-define=API_BASE=` (empty), the app uses the address it was
/// opened from, so one web server can serve the app and forward /api to Django.
const defaultApiBase = String.fromEnvironment('API_BASE', defaultValue: 'http://10.0.2.2:8000');

String initialApiBase() => defaultApiBase.isEmpty && kIsWeb ? Uri.base.origin : defaultApiBase;

class SecureTokenStore implements TokenStore {
  static const _key = 'refresh_token';
  final _storage = const FlutterSecureStorage();
  @override
  Future<String?> readRefresh() => _storage.read(key: _key);
  @override
  Future<void> writeRefresh(String? token) =>
      token == null ? _storage.delete(key: _key) : _storage.write(key: _key, value: token);
}

/// Session, active organization/event and language. Screens read from here and call
/// [api] directly for their own data.
class AppState extends ChangeNotifier {
  AppState({required this.api, SharedPreferences? prefs}) : _prefs = prefs {  // ignore: prefer_initializing_formals
    api.onSessionExpired = () {
      _clearSession();
      notifyListeners();
    };
  }

  final ApiClient api;
  SharedPreferences? _prefs;

  bool ready = false;
  Map<String, dynamic>? user;
  List<Map<String, dynamic>> organizations = [];
  Map<String, dynamic>? orgDetail; // GET /me/organizations/{id}/
  List<Map<String, dynamic>> events = [];
  Map<String, dynamic>? event;

  String get language => api.language;
  bool get loggedIn => user != null;
  String? get orgId => api.orgId;
  String? get eventId => event?['id'] as String?;
  Map<String, dynamic> get permissions =>
      (orgDetail?['permissions'] as Map?)?.cast<String, dynamic>() ?? const {};
  bool can(String perm) => permissions.containsKey(perm);
  String get roleCode => (orgDetail?['role'] as Map?)?['code']?.toString() ?? '';
  String get orgName => (orgDetail?['organization'] as Map?)?['name']?.toString() ?? '';
  String? get logoUrl => (orgDetail?['organization'] as Map?)?['logo_url']?.toString();

  /// Admin studio: how this organization's admins set up the Collect form.
  Map<String, dynamic> get formStudio => (orgDetail?['form_studio'] as Map?)?.cast<String, dynamic>() ?? const {};

  /// The admin's own name for a Collect field, or [fallback] for the standard one.
  String fieldLabel(String field, String fallback) {
    final label = (formStudio['labels'] as Map?)?[field];
    return label is String && label.isNotEmpty ? label : fallback;
  }

  Map? _studioMode(String mode) => (formStudio['modes'] as Map?)?[mode] as Map?;
  String? customModeLabel(String mode) {
    final label = _studioMode(mode)?['label'];
    return label is String && label.isNotEmpty ? label : null;
  }

  bool modeHidden(String mode) => _studioMode(mode)?['hidden'] == true;

  /// The organization's own dropdowns shown on Collect.
  List<Map<String, dynamic>> get customFields => [
    for (final f in (formStudio['custom_fields'] as List? ?? const []))
      if (f is Map && f['active'] != false && f['key'] != null) f.cast<String, dynamic>(),
  ];

  /// Committee roles that collect money get the collector screens.
  bool get isCollector => can('payments.create');

  /// Members (or anyone linked to a member record) get the portal screens.
  bool get isMember => roleCode == 'member' || (!isCollector && can('portal.self'));

  String t(String key, [Map<String, String> args = const {}]) => tr(language, key, args);

  Future<void> load() async {
    _prefs ??= await SharedPreferences.getInstance();
    api.baseUrl = _prefs!.getString('api_base') ?? initialApiBase();
    api.language = _prefs!.getString('language') ?? 'en';
    final savedOrg = _prefs!.getString('org_id');
    try {
      if (await api.refresh()) {
        await _afterLogin(preferredOrg: savedOrg);
      }
    } catch (_) {
      // Offline at start: show the login page; the user can retry.
      _clearSession();
    }
    ready = true;
    notifyListeners();
  }

  Future<void> setApiBase(String url) async {
    var u = url.trim();
    while (u.endsWith('/')) {
      u = u.substring(0, u.length - 1);
    }
    if (u.endsWith('/api/v1')) u = u.substring(0, u.length - 7);
    api.baseUrl = u;
    await _prefs?.setString('api_base', u);
    notifyListeners();
  }

  Future<void> setLanguage(String lang, {bool syncProfile = true}) async {
    if (!supportedLanguages.containsKey(lang)) return;
    api.language = lang;
    await _prefs?.setString('language', lang);
    notifyListeners();
    if (syncProfile && loggedIn) {
      try {
        await api.patch('/me/', {'preferred_language': lang});
      } catch (_) {
        // Labels change locally even if the profile update fails.
      }
    }
  }

  Future<void> loginWithPassword(String identifier, String password) async {
    final auth = await api.post('/auth/login/', {'identifier': identifier.trim(), 'password': password});
    await api.saveSession((auth as Map).cast<String, dynamic>());
    await _afterLogin(preferredOrg: _prefs?.getString('org_id'));
  }

  Future<Map<String, dynamic>> requestOtp(String mobile) async {
    final r = await api.post('/auth/otp/request/', {'mobile': mobile.trim()});
    return (r as Map).cast<String, dynamic>();
  }

  Future<void> verifyOtp(String mobile, String code) async {
    final auth = await api.post('/auth/otp/verify/', {'mobile': mobile.trim(), 'code': code.trim()});
    await api.saveSession((auth as Map).cast<String, dynamic>());
    await _afterLogin(preferredOrg: _prefs?.getString('org_id'));
  }

  Future<void> _afterLogin({String? preferredOrg}) async {
    user = ((await api.get('/me/')) as Map).cast<String, dynamic>();
    final lang = user?['preferred_language']?.toString();
    if (lang != null && supportedLanguages.containsKey(lang) && _prefs?.getString('language') == null) {
      await setLanguage(lang, syncProfile: false);
    }
    organizations = resultsOf(await api.get('/me/organizations/'));
    final ids = organizations.map((o) => o['id']).toSet();
    if (preferredOrg != null && ids.contains(preferredOrg)) {
      await selectOrganization(preferredOrg, notify: false);
    } else if (organizations.length == 1) {
      await selectOrganization(organizations.first['id'] as String, notify: false);
    } else {
      api.orgId = null;
      orgDetail = null;
    }
    notifyListeners();
  }

  Future<void> selectOrganization(String id, {bool notify = true}) async {
    api.orgId = id;
    await _prefs?.setString('org_id', id);
    orgDetail = ((await api.get('/me/organizations/$id/')) as Map).cast<String, dynamic>();
    await loadEvents();
    if (notify) notifyListeners();
  }

  Future<void> loadEvents() async {
    if (isMember && !isCollector) {
      // Members only see events through the portal.
      try {
        final me = await api.get('/portal/me/');
        events = resultsOf((me as Map)['events']);
      } on ApiException {
        events = [];
      }
    } else {
      events = resultsOf(await api.get('/events/', query: {'status': 'active'}));
    }
    final saved = _prefs?.getString('event_id:${api.orgId}');
    event = events.where((e) => e['id'] == saved).firstOrNull ?? (events.isNotEmpty ? events.first : null);
  }

  Future<void> selectEvent(String id) async {
    event = events.firstWhere((e) => e['id'] == id);
    await _prefs?.setString('event_id:${api.orgId}', id);
    notifyListeners();
  }

  Future<void> logout() async {
    await api.logout();
    _clearSession();
    await _prefs?.remove('org_id');
    notifyListeners();
  }

  void _clearSession() {
    user = null;
    organizations = [];
    orgDetail = null;
    events = [];
    event = null;
    api.orgId = null;
    api.accessToken = null;
  }
}
