import 'dart:async';
import 'dart:io';

import 'package:razorpay_flutter/razorpay_flutter.dart';

import 'checkout_stub.dart' show CheckoutResult;
export 'checkout_stub.dart' show CheckoutResult;

bool get checkoutSupported => Platform.isAndroid || Platform.isIOS;

/// Opens Razorpay with the order the server created. The server only issues a receipt
/// after it checks Razorpay's signature, so the app never marks anything paid itself.
Future<CheckoutResult> openCheckout(Map<String, dynamic> checkout) {
  final razorpay = Razorpay();
  final done = Completer<CheckoutResult>();
  razorpay.on(Razorpay.EVENT_PAYMENT_SUCCESS, (PaymentSuccessResponse r) {
    if (!done.isCompleted) done.complete(CheckoutResult.success(r.orderId, r.paymentId, r.signature));
  });
  razorpay.on(Razorpay.EVENT_PAYMENT_ERROR, (PaymentFailureResponse r) {
    if (!done.isCompleted) done.complete(CheckoutResult.failed());
  });
  razorpay.on(Razorpay.EVENT_EXTERNAL_WALLET, (ExternalWalletResponse r) {});
  razorpay.open({
    'key': checkout['key'],
    'order_id': checkout['order_id'],
    'amount': checkout['amount'],
    'currency': checkout['currency'],
    'name': checkout['name'],
    'description': checkout['description'],
    'prefill': checkout['prefill'] ?? {},
  });
  return done.future.whenComplete(razorpay.clear);
}
