import 'dart:async';
import 'dart:convert';
import 'package:flet/flet.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

class IronCycleBillingControl extends FletService {
  IronCycleBillingControl({required super.control});
  final InAppPurchase _billing = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _subscription;
  final Map<String, ProductDetails> _products = {};
  Completer<Map<String, dynamic>>? _pendingOperation;
  String? _pendingProductId;
  String? _pendingKind;
  Map<String, dynamic>? _lastEvent;

  @override
  void init() {
    super.init();
    control.addInvokeMethodListener(_invokeMethod);
    _subscription = _billing.purchaseStream.listen(
      _onPurchases,
      onError: (Object error, StackTrace stack) {
        final result = {'status': 'stream_error', 'owned': false, 'message': error.toString()};
        _lastEvent = result;
        _completePending(result);
      },
    );
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    final arguments = args is Map ? Map<String, dynamic>.from(args) : <String, dynamic>{};
    switch (name) {
      case 'is_available': return _billing.isAvailable();
      case 'query_product': return jsonEncode(await _queryProduct(_requiredProductId(arguments)));
      case 'purchase': return jsonEncode(await _purchase(_requiredProductId(arguments)));
      case 'restore': return jsonEncode(await _restore(_requiredProductId(arguments), quiet: false));
      case 'reconcile': return jsonEncode(await _restore(_requiredProductId(arguments), quiet: true));
      case 'take_event':
        final event = _lastEvent ?? {'status': 'none'};
        _lastEvent = null;
        return jsonEncode(event);
      default: throw Exception('Unknown IronCycleBilling method: $name');
    }
  }

  String _requiredProductId(Map<String, dynamic> args) {
    final value = args['product_id']?.toString().trim() ?? '';
    if (value.isEmpty) throw ArgumentError('product_id is required');
    return value;
  }

  Future<Map<String, dynamic>> _queryProduct(String productId) async {
    if (!await _billing.isAvailable()) return {'available': false, 'status': 'billing_unavailable'};
    final response = await _billing.queryProductDetails({productId});
    if (response.error != null) return {'available': false, 'status': 'error', 'message': response.error!.message, 'code': response.error!.code};
    if (response.productDetails.isEmpty) return {'available': false, 'status': 'not_found', 'not_found_ids': response.notFoundIDs};
    final product = response.productDetails.first;
    _products[productId] = product;
    return {'available': true, 'status': 'ready', 'product_id': product.id, 'title': product.title, 'description': product.description, 'price': product.price, 'currency_code': product.currencyCode, 'raw_price': product.rawPrice};
  }

  Future<Map<String, dynamic>> _purchase(String productId) async {
    final queried = await _queryProduct(productId);
    if (queried['available'] != true) return queried;
    if (_pendingOperation != null) return {'status': 'busy', 'owned': false};
    _pendingProductId = productId; _pendingKind = 'purchase';
    _pendingOperation = Completer<Map<String, dynamic>>();
    final launched = await _billing.buyNonConsumable(purchaseParam: PurchaseParam(productDetails: _products[productId]!));
    if (!launched) _completePending({'status': 'not_launched', 'owned': false});
    final future = _pendingOperation!.future;
    return future.timeout(const Duration(minutes: 5), onTimeout: () {
      _clearPending(); return {'status': 'timeout', 'owned': false, 'inconclusive': true};
    });
  }

  Future<Map<String, dynamic>> _restore(String productId, {required bool quiet}) async {
    if (!await _billing.isAvailable()) return {'status': 'billing_unavailable', 'owned': false, 'inconclusive': true};
    if (_pendingOperation != null) return {'status': 'busy', 'owned': false, 'inconclusive': true};
    _pendingProductId = productId; _pendingKind = quiet ? 'reconcile' : 'restore';
    _pendingOperation = Completer<Map<String, dynamic>>();
    try { await _billing.restorePurchases(); }
    catch (error) { _clearPending(); return {'status': 'error', 'owned': false, 'inconclusive': true, 'message': error.toString()}; }
    final future = _pendingOperation!.future;
    return future.timeout(const Duration(seconds: 20), onTimeout: () {
      _clearPending();
      return quiet
        ? {'status': 'inconclusive', 'owned': false, 'inconclusive': true}
        : {'status': 'not_owned', 'owned': false, 'inconclusive': false};
    });
  }

  Future<void> _onPurchases(List<PurchaseDetails> purchases) async {
    for (final purchase in purchases) {
      if (_pendingProductId != null && purchase.productID != _pendingProductId) continue;
      final result = <String, dynamic>{'product_id': purchase.productID, 'transaction_date': purchase.transactionDate};
      switch (purchase.status) {
        case PurchaseStatus.pending:
          result.addAll({'status': 'pending', 'owned': false, 'inconclusive': true});
          _lastEvent = result;
          _completePending(result);
          continue;
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          try {
            if (purchase.pendingCompletePurchase) await _billing.completePurchase(purchase);
          } catch (error) {
            result.addAll({'status': 'completion_error', 'owned': false, 'inconclusive': true, 'message': error.toString()});
            _lastEvent = result; _completePending(result); continue;
          }
          result.addAll({'status': purchase.status == PurchaseStatus.restored ? 'restored' : 'purchased', 'owned': true, 'verification_source': purchase.verificationData.source});
          break;
        case PurchaseStatus.canceled:
          result.addAll({'status': 'canceled', 'owned': false, 'inconclusive': false});
          break;
        case PurchaseStatus.error:
          result.addAll({'status': 'error', 'owned': false, 'inconclusive': true, 'message': purchase.error?.message, 'code': purchase.error?.code});
          break;
      }
      _lastEvent = result;
      _completePending(result);
    }
  }

  void _clearPending() { _pendingOperation = null; _pendingProductId = null; _pendingKind = null; }
  void _completePending(Map<String, dynamic> result) {
    final completer = _pendingOperation; _clearPending();
    if (completer != null && !completer.isCompleted) completer.complete(result);
  }
  @override
  void dispose() { control.removeInvokeMethodListener(_invokeMethod); _subscription?.cancel(); super.dispose(); }
}
