import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vargani_app/api/api_client.dart';
import 'package:vargani_app/main.dart';
import 'package:vargani_app/state/app_state.dart';
import 'package:vargani_app/util/theme.dart';

/// A small fake of the Vargani API with the response shapes the real server returns.
class FakeApi {
  FakeApi({required this.role});
  final String role; // collector | member
  final requests = <http.Request>[];
  final collections = <Map<String, dynamic>>[];

  static const org = 'org-1', event = 'ev-1', ct = 'ct-1';

  Map<String, dynamic> get permissions => switch (role) {
    'collector' => {'payments.create': 'assigned', 'receipts.view': 'own', 'receipts.share': 'own', 'portal.self': 'self'},
    'treasurer' => {'payments.create': 'all', 'payments.view': 'all', 'receipts.view': 'all'},
    'org_admin' => {'payments.create': 'all', 'members.view': 'all', 'members.manage': 'all'},
    'pavti_admin' => {'payments.create': 'all', 'payments.view': 'all', 'receipts.view': 'all', 'receipts.share': 'all',
      'records.admin_edit': 'all', 'reports.export': 'all', 'people.view': 'all'},
    _ => {'portal.self': 'self'},
  };

  http.Response _json(Object body, [int status = 200]) =>
      http.Response.bytes(utf8.encode(jsonEncode(body)), status, headers: {'content-type': 'application/json'});

  Future<http.Response> handle(http.Request r) async {
    requests.add(r);
    final p = r.url.path.replaceFirst('/api/v1', '');
    switch ((r.method, p)) {
      case ('POST', '/auth/login/'):
        final b = jsonDecode(r.body);
        if (b['password'] != 'right') {
          return _json({'error': {'code': 'invalid_credentials', 'message': 'Wrong login details.', 'details': {}}}, 400);
        }
        return _json({'access': 'A', 'refresh': 'R', 'user': {}});
      case ('POST', '/auth/otp/request/'):
        return _json({'verification': {'destination': '+91******122', 'channel': 'sms'}, 'debug_code': '123456'});
      case ('POST', '/auth/otp/verify/'):
        return _json({'access': 'A', 'refresh': 'R', 'user': {}});
      case ('GET', '/me/'):
        return _json({'id': role == 'collector' ? 'u-2' : 'u-1', 'full_name': role == 'collector' ? 'Kiran' : 'Ritesh',
          'preferred_language': 'en'});
      case ('PATCH', '/me/'):
        return _json({});
      case ('GET', '/me/organizations/'):
        return _json([
          {'id': org, 'name': 'Demo Mandal', 'logo_url': null, 'role': {'code': role, 'name': role}}
        ]);
      case ('GET', '/me/organizations/$org/'):
        return _json({
          'organization': {'id': org, 'name': 'Demo Mandal', 'logo_url': null},
          'role': {'code': role, 'name': role},
          'permissions': permissions,
        });
      case ('GET', '/events/'):
        return _json({'count': 1, 'next': null, 'results': [
          {'id': event, 'name': 'Ganesh Chaturthi 2026', 'start_date': '2026-08-01', 'end_date': '2026-12-31'}
        ]});
      case ('GET', '/notifications/unread-count/'):
        return _json({'unread': 2});
      case ('GET', '/collectors/me/dashboard/'):
        return _json({'today': '651.00', 'this_week': '651.00', 'this_month': '1651.00', 'total': '110000.50',
          'by_mode': {'cash': '0.00', 'upi': '651.00'}, 'assigned': 2, 'paid_this_month': 1, 'recent_receipts': [],
          'collector': 'm-1'});
      case ('GET', '/people/'):
        return _json({'count': 1, 'next': null, 'results': [
          {'id': 'p-1', 'full_name': 'Sunita More', 'mobile': '+919822001133', 'area': 'Shivaji Nagar'}
        ]});
      case ('GET', '/contribution-types/'):
        return _json({'count': 1, 'next': null, 'results': [
          {'id': ct, 'name': 'Ganesh Vargani', 'fund_name': 'Utsav Fund', 'kind': 'one_time',
           'suggested_min': '500.00', 'suggested_max': '700.00'}
        ]});
      case ('POST', '/collections/'):
        final b = jsonDecode(r.body) as Map<String, dynamic>;
        collections.add({...b, 'key': r.headers['Idempotency-Key']});
        return _json({'id': 'pay-1', 'amount': '651.00', 'receipt': {'id': 'rc-1', 'receipt_number': 'GC-2026-00002'}}, 201);
      case ('GET', '/payments/'):
        return _json({'count': 2, 'next': null, 'results': [
          {'id': 'pay-2', 'event': event, 'event_name': 'Ganesh Chaturthi 2026', 'status': 'successful',
           'amount': '500.00', 'balance_due': '151.00', 'pavti_status': 'partly_paid', 'follow_up_on': '2026-10-30',
           'follow_up_state': 'upcoming', 'mode': 'cash', 'paid_at': '2026-10-20T10:00:00Z', 'payer_name': 'Sunita More',
           'collector_name': 'Kiran', 'receipt': {'id': 'rc-2', 'receipt_number': 'GC-2026-00003'},
           'created_at': '2026-10-20T10:00:05Z', 'created_by_name': 'Kiran Collector',
           'lines': [{'contribution_type_name': 'Donation', 'period_month': null}]},
          {'id': 'pay-1', 'event': 'ev-0', 'event_name': 'Navratri 2025', 'status': 'successful', 'amount': '300.00',
           'balance_due': '0.00', 'pavti_status': 'paid', 'mode': 'upi', 'paid_at': '2025-10-01T10:00:00Z',
           'payer_name': 'Sunita More', 'receipt': {'id': 'rc-1', 'receipt_number': 'NV-2025-00001'},
           'lines': [{'contribution_type_name': 'Monthly Contribution', 'period_month': '2025-10-01'}]},
        ]});
      case ('GET', '/dues/'):
        return _json({'count': 0, 'next': null, 'results': []});
      case ('GET', '/dashboard/summary/'):
        return _json({'follow_ups': {'overdue': 0, 'due_today': 0, 'owing': 1, 'balance': '151.00', 'paid': 4}});
      case ('GET', '/receipts/rc-1/'):
        return _json(_receipt);
      case ('GET', '/receipts/'):
        return _json({'count': 1, 'next': null, 'results': [
          {'id': 'rc-1', 'receipt_number': 'GC-2026-00002', 'status': 'issued', 'payer_name': 'Sunita More',
           'amount': '651.00', 'issued_at': '2026-10-07T15:55:51Z', 'paid_at': '2026-10-07T15:55:51Z'}
        ]});
      case ('GET', '/payments/pay-1/'):
        return _json({'id': 'pay-1', 'payer_name': 'Sunita More', 'notes': '', 'keeps_balance': true,
          'receipt': {'id': 'rc-1', 'receipt_number': 'GC-2026-00002'},
          'lines': [{'id': 'l-1', 'contribution_type_name': 'Ganesh Vargani', 'amount': '651.00', 'period_month': null}]});
      case ('POST', '/payments/pay-1/edit/'):
        return _json({'id': 'pay-1', 'amount': '600.00'});
      case ('GET', '/members/'):
        return _json({'count': 2, 'next': null, 'results': [
          {'id': 'm-1', 'status': 'active', 'can_reset_password': false,
           'role': {'id': 'r-admin', 'code': 'org_admin', 'name': 'Organization Admin'},
           'user': {'id': 'u-1', 'full_name': 'Ritesh', 'username': 'ritesh', 'email': null, 'mobile': null}},
          {'id': 'm-2', 'status': 'active', 'can_reset_password': true,
           'role': {'id': 'r-col', 'code': 'collector', 'name': 'Collector'},
           'user': {'id': 'u-2', 'full_name': 'Kiran', 'username': 'kiran', 'email': null, 'mobile': '+919822001144'}},
        ]});
      case ('GET', '/roles/'):
        return _json([
          {'id': 'r-admin', 'code': 'org_admin', 'name': 'Organization Admin'},
          {'id': 'r-col', 'code': 'collector', 'name': 'Collector'},
        ]);
      case ('POST', '/members/'):
        final b = jsonDecode(r.body) as Map<String, dynamic>;
        return _json({'id': 'm-3', 'status': 'active', 'new_login': true, 'can_reset_password': true,
          'role': {'id': b['role_id'], 'code': 'collector', 'name': 'Collector'},
          'user': {'id': 'u-3', 'full_name': b['full_name'], 'username': b['username'], 'email': null, 'mobile': null}}, 201);
      case ('PATCH', '/members/m-2/'):
        return _json({});
      case ('POST', '/members/m-2/remove/'):
        return http.Response('', 204);
      case ('GET', '/portal/me/'):
        return _json({'person': {'full_name': 'Ritesh Patil'}, 'organization': {'name': 'Demo Mandal'},
          'events': [{'id': event, 'name': 'Ganesh Chaturthi 2026', 'status': 'active'}], 'online_payments': true});
      case ('GET', '/portal/summary/'):
        return _json({'total_paid': '300.00', 'total_due': '300.00', 'by_type': [], 'dues': [
          {'contribution_type': ct, 'name': 'Ganesh Vargani', 'expected': '600.00', 'paid': '300.00', 'due': '300.00'}
        ]});
    }
    return _json({'error': {'code': 'not_found', 'message': 'Not found: ${r.method} $p', 'details': {}}}, 404);
  }

  static final _receipt = {
    'id': 'rc-1', 'receipt_number': 'GC-2026-00002', 'status': 'issued', 'amount': '651.00', 'logo_url': null,
    'payment': 'pay-1', 'language': 'en',
    'snapshot': {
      'organization': {'name': 'Demo Mandal', 'address': 'Pune'},
      'person': {'name': 'Sunita More', 'mobile': '+919822001133'},
      'event': {'name': 'Ganesh Chaturthi 2026'},
      'lines': [{'contribution_type': 'Ganesh Vargani', 'fund': 'Utsav Fund', 'amount': '651.00'}],
      'total': '651.00', 'mode': 'upi', 'reference_number': 'UPI123', 'collector': 'Kiran',
      'paid_at': '2026-10-07T15:55:51Z',
    },
  };
}

Future<(AppState, FakeApi)> start(WidgetTester tester, String role) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  final fake = FakeApi(role: role);
  final state = AppState(
    api: ApiClient(baseUrl: 'https://api.test', tokens: MemoryTokenStore(), httpClient: MockClient(fake.handle)),
    prefs: prefs,
  );
  await tester.binding.setSurfaceSize(const Size(420, 900));
  await tester.pumpWidget(VarganiApp(state: state));
  await state.load();
  await tester.pumpAndSettle();
  return (state, fake);
}

void main() {
  testWidgets('collector logs in, records a collection once and sees the receipt', (tester) async {
    final (_, fake) = await start(tester, 'collector');

    await tester.enterText(find.byKey(const Key('login-identifier')), 'kiran@demo.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'wrong');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();
    expect(find.text('Wrong login details.'), findsOneWidget);
    // Let the error message close so it does not cover the Save button later.
    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('login-password')), 'right');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();

    // Organization picked automatically (only one); dashboard for the active event.
    expect(find.text('Demo Mandal'), findsOneWidget);
    expect(find.text('Ganesh Chaturthi 2026'), findsOneWidget);
    expect(find.text('₹1,10,000.50'), findsOneWidget);
    expect(find.text('2'), findsWidgets); // unread badge

    await tester.tap(find.text('People'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sunita More'));
    await tester.pumpAndSettle();

    // Only one type: preselected. Bad amount shows a local error.
    await tester.enterText(find.byKey(const Key('collect-amount-0')), '12.345');
    await tester.pump();
    expect(find.text('Enter an amount such as 500 or 750.50'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('collect-amount-0')), '651');
    await tester.tap(find.byKey(const Key('mode-upi')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('collect-reference')), 'UPI123');
    expect(find.byKey(const Key('collect-total')), findsOneWidget);
    expect(find.text('₹651'), findsWidgets);
    // Part of it came now: the rest is kept as balance and the Save button says so.
    await tester.enterText(find.byKey(const Key('collect-received')), '500');
    await tester.pumpAndSettle();
    expect(find.text('Balance ₹151 will be shown on the receipt and in Balance due.'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('collect-save')),
      200,
      scrollable: find.descendant(of: find.byKey(const Key('collect-form')), matching: find.byType(Scrollable)).first,
    );
    expect(find.text('Save ₹500 received, ₹151 balance, and issue receipt'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('collect-save')));
    await tester.tap(find.byKey(const Key('collect-save')));
    await tester.pumpAndSettle();

    expect(fake.collections, hasLength(1));
    final c = fake.collections.single;
    expect(c['payer'], 'p-1');
    expect(c['mode'], 'upi');
    expect(c['reference_number'], 'UPI123');
    expect(c['lines'], [{'contribution_type': 'ct-1', 'amount': '651.00'}]);
    expect(c['received'], '500.00');
    expect(c['follow_up_on'], isNotNull);
    expect(c['status'], 'successful');
    expect(c.containsKey('paid_at'), isFalse); // today: the server records the time
    expect(c['key'], isNotEmpty);
    expect(fake.requests.last.headers['X-Organization-ID'], 'org-1');

    expect(find.text('Receipt issued'), findsWidgets);
    expect(find.text('Receipt no. GC-2026-00002'), findsOneWidget);
    expect(find.byKey(const Key('receipt-whatsapp')), findsOneWidget);
  });

  testWidgets('member logs in with an SMS code and sees dues in Marathi', (tester) async {
    final (state, fake) = await start(tester, 'member');

    await tester.tap(find.text('Member'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('otp-mobile')), '9822001122');
    await tester.tap(find.byKey(const Key('otp-send')));
    await tester.pumpAndSettle();
    expect(find.text('Code sent to +91******122'), findsOneWidget);
    await tester.tap(find.byKey(const Key('otp-verify')));
    await tester.pumpAndSettle();

    expect(find.text('Ritesh Patil'), findsOneWidget);
    expect(find.text('Ganesh Vargani'), findsOneWidget);
    expect(find.byKey(const Key('member-pay')), findsOneWidget);
    expect(find.text('Collect'), findsNothing); // no collector screens for members

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('lang-mr')));
    await tester.pumpAndSettle();
    expect(state.language, 'mr');
    expect(find.text('सेटिंग्ज'), findsWidgets);
    final patch = fake.requests.where((r) => r.method == 'PATCH').single;
    expect(jsonDecode(patch.body), {'preferred_language': 'mr'});
    expect(fake.requests.last.headers['Accept-Language'], 'mr');
  });

  testWidgets('a user picks their own app color and the whole app repaints', (tester) async {
    final (state, fake) = await start(tester, 'member');
    await tester.tap(find.text('Member'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('otp-mobile')), '9822001122');
    await tester.tap(find.byKey(const Key('otp-send')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('otp-verify')));
    await tester.pumpAndSettle();
    expect(state.themeColor, 'orange');

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('org-theme')), findsNothing); // only organization admins set the default
    await tester.scrollUntilVisible(find.byKey(const Key('theme-blue')), 200);
    await tester.tap(find.byKey(const Key('theme-blue')));
    await tester.pumpAndSettle();

    expect(state.themeColor, 'blue');
    final patch = fake.requests.where((r) => r.method == 'PATCH').single;
    expect(jsonDecode(patch.body), {'theme_color': 'blue'});
    final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
    expect(app.theme!.colorScheme.primary, isNot(buildTheme('orange', Brightness.light).colorScheme.primary));

    await tester.tap(find.byKey(const Key('theme-org')));
    await tester.pumpAndSettle();
    expect(state.themeColor, 'orange');
  });

  testWidgets('a person opens their contribution history across events, then Collect', (tester) async {
    await start(tester, 'treasurer');
    await tester.enterText(find.byKey(const Key('login-identifier')), 'asha@demo.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'right');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();

    await tester.tap(find.text('People'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sunita More'));
    await tester.pumpAndSettle();

    expect(find.text('Contribution history'), findsOneWidget);
    expect(find.text('₹800'), findsOneWidget); // total paid across both events
    expect(find.text('₹151'), findsOneWidget); // still owed
    expect(find.text('Donation'), findsOneWidget);
    expect(find.text('Partly paid'), findsOneWidget);

    await tester.tap(find.byKey(const Key('history-event')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Navratri 2025').last);
    await tester.pumpAndSettle();
    expect(find.text('Donation'), findsNothing);
    expect(find.text('Monthly Contribution (Oct 2025)'), findsOneWidget);
    expect(find.text('₹300'), findsWidgets);

    await tester.tap(find.byKey(const Key('person-collect')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('collect-amount-0')), findsOneWidget);
  });

  testWidgets('dashboard cards open the list behind them, sorted and with who created each payment', (tester) async {
    final (_, fake) = await start(tester, 'treasurer');
    await tester.enterText(find.byKey(const Key('login-identifier')), 'asha@demo.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'right');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();

    // "Check a day" asks the dashboard for today only and shows fully paid pavtis.
    final day = fake.requests.lastWhere((r) => r.url.path.endsWith('/dashboard/summary/') && r.url.queryParameters.containsKey('date_from'));
    expect(day.url.queryParameters['date_from'], day.url.queryParameters['date_to']);
    expect(find.byKey(const Key('day-paid')), findsOneWidget);

    await tester.tap(find.byKey(const Key('card-total')));
    await tester.pumpAndSettle();
    final list = fake.requests.last;
    expect(list.url.path, endsWith('/payments/'));
    expect(list.url.queryParameters['collector'], 'm-1');
    expect(list.url.queryParameters['status'], 'successful');
    expect(list.url.queryParameters['ordering'], '-paid_at');
    expect(find.textContaining('by Kiran Collector'), findsOneWidget);

    await tester.tap(find.byKey(const Key('list-direction')));
    await tester.pumpAndSettle();
    expect(fake.requests.last.url.queryParameters['ordering'], 'paid_at');
    await tester.tap(find.byKey(const Key('list-today')));
    await tester.pumpAndSettle();
    expect(fake.requests.last.url.queryParameters['date_from'], isNotNull);
  });

  testWidgets('an admin logs in with a username and manages users', (tester) async {
    final (_, fake) = await start(tester, 'org_admin');
    await tester.enterText(find.byKey(const Key('login-identifier')), 'ritesh');
    await tester.enterText(find.byKey(const Key('login-password')), 'right');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();
    expect(jsonDecode(fake.requests.firstWhere((r) => r.url.path.endsWith('/auth/login/')).body)['identifier'], 'ritesh');

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('manage-users')));
    await tester.pumpAndSettle();
    expect(find.text('Ritesh (you)'), findsOneWidget);
    expect(find.text('kiran · Collector'), findsOneWidget);

    // Add a collector with only a username and a password.
    await tester.tap(find.byKey(const Key('fab-add-user')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('add-user-name')), 'Ramesh Pawar');
    await tester.enterText(find.byKey(const Key('add-user-username')), 'ramesh');
    await tester.enterText(find.byKey(const Key('user-password-field')), 'Kmrt-4829-Pqws');
    await tester.tap(find.byKey(const Key('add-user-save')));
    await tester.pumpAndSettle();
    final added = jsonDecode(fake.requests.lastWhere((r) => r.method == 'POST' && r.url.path.endsWith('/members/')).body);
    expect(added['username'], 'ramesh');
    expect(added['role_id'], 'r-col');
    expect(added['mobile'], isNull);
    expect(find.textContaining('Login: ramesh'), findsOneWidget);
    await tester.tap(find.text('Close'));
    await tester.pumpAndSettle();

    // Deactivate, then delete Kiran.
    await tester.tap(find.text('Kiran'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('user-status')));
    await tester.pumpAndSettle();
    final patch = fake.requests.lastWhere((r) => r.method == 'PATCH');
    expect(patch.url.path, '/api/v1/members/m-2/');
    expect(jsonDecode(patch.body), {'status': 'suspended'});

    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Kiran'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('user-delete')));
    await tester.pumpAndSettle();
    expect(find.text('Delete Kiran?'), findsOneWidget);
    await tester.tap(find.byKey(const Key('confirm-delete')));
    await tester.pumpAndSettle();
    expect(fake.requests.any((r) => r.method == 'POST' && r.url.path == '/api/v1/members/m-2/remove/'), isTrue);
    expect(find.text('User deleted'), findsOneWidget);
  });

  testWidgets('an admin finds a pavti by its number, corrects the amount and downloads contacts', (tester) async {
    final (_, fake) = await start(tester, 'pavti_admin');
    await tester.enterText(find.byKey(const Key('login-identifier')), 'ritesh');
    await tester.enterText(find.byKey(const Key('login-password')), 'right');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();

    await tester.tap(find.text('People').last);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('people-download')), findsOneWidget);

    await tester.tap(find.text('Receipts').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('receipts-search')), 'GC-2026-00002');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    final search = fake.requests.lastWhere((r) => r.url.path == '/api/v1/receipts/');
    expect(search.url.queryParameters['search'], 'GC-2026-00002');

    await tester.tap(find.text('Sunita More'));
    await tester.pumpAndSettle();
    // The collector's name is printed above "Authorised signatory".
    expect(find.descendant(of: find.byKey(const Key('receipt-signatory')), matching: find.text('Kiran')), findsOneWidget);
    expect(find.text('Authorised signatory'), findsOneWidget);

    await tester.ensureVisible(find.byKey(const Key('receipt-edit')));
    await tester.tap(find.byKey(const Key('receipt-edit')));
    await tester.pumpAndSettle();
    expect(find.text('This pavti keeps a balance: the difference moves to the balance still owed.'), findsOneWidget);
    await tester.enterText(find.byKey(const Key('pavti-amount-l-1')), '600');
    await tester.tap(find.byKey(const Key('pavti-save')));
    await tester.pumpAndSettle();
    final edit = fake.requests.lastWhere((r) => r.method == 'POST' && r.url.path == '/api/v1/payments/pay-1/edit/');
    expect(jsonDecode(edit.body)['line_amounts'], {'l-1': '600'});
    expect(find.text('Receipt no. GC-2026-00002'), findsOneWidget);
  });
}
