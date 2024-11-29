from .device import get_device_type
from .changelog import get_changelog

def get_device_type(request):
    """
    Return the type of device making the request based on User-Agent
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'

__all__ = ['get_device_type', 'get_changelog']