/// Result of the Razorpay checkout sheet.
class CheckoutResult {
  CheckoutResult.success(this.orderId, this.paymentId, this.signature) : ok = true;
  CheckoutResult.failed() : ok = false, orderId = null, paymentId = null, signature = null;
  final bool ok;
  final String? orderId, paymentId, signature;
}

const checkoutSupported = false;

Future<CheckoutResult> openCheckout(Map<String, dynamic> checkout) async => CheckoutResult.failed();
