class ApArError(Exception):
    """Base exception for apps.ap_ar."""


class AlreadyCancelledError(ApArError):
    pass


class HasPaymentsError(ApArError):
    pass


class OverpaymentError(ApArError):
    pass
