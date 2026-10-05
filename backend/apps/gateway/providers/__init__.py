from .razorpay import RazorpayClient

CLIENTS = {"razorpay": RazorpayClient}


def client_for(config):
    return CLIENTS[config.provider](config)
