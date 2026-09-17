import 'package:flet/flet.dart';
import 'billing.dart';

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    if (control.type == 'IronCycleBilling') {
      return IronCycleBillingControl(control: control);
    }
    return null;
  }
}
