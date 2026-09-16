import logging

logger = logging.getLogger('audit')


def parse_device_info(user_agent_str):
    """
    تحليل ترويسة User-Agent وتحويلها إلى نوع الجهاز والمتصفح بشكل مقروء وأنيق
    (مثال: iPhone • Safari / Windows PC • Chrome / Android • Chrome)
    """
    if not user_agent_str:
        return "غير محدد"

    ua = user_agent_str
    device = "كمبيوتر"
    browser = "متصفح"

    # 1. كشف نوع الجهاز ونظام التشغيل
    if "iPhone" in ua:
        device = "iPhone"
    elif "iPad" in ua:
        device = "iPad"
    elif "Android" in ua:
        if "Mobile" in ua:
            device = "Android Phone"
        else:
            device = "Android Tablet"
    elif "Windows NT 10.0" in ua or "Windows NT 11.0" in ua:
        device = "Windows PC"
    elif "Windows" in ua:
        device = "Windows"
    elif "Macintosh" in ua or "Mac OS" in ua:
        device = "Mac"
    elif "Linux" in ua:
        device = "Linux"

    # 2. كشف نوع المتصفح بدقة
    if "Edg/" in ua or "Edge/" in ua:
        browser = "Edge"
    elif "OPR/" in ua or "Opera/" in ua:
        browser = "Opera"
    elif "Chrome" in ua and "Chromium" not in ua and "Edg" not in ua and "OPR" not in ua:
        browser = "Chrome"
    elif "Safari" in ua and "Chrome" not in ua and "Android" not in ua:
        browser = "Safari"
    elif "Firefox" in ua:
        browser = "Firefox"
    elif "MobileSafari" in ua or "AppleWebKit" in ua and "iPhone" in ua:
        browser = "Safari"

    return f"{device} • {browser}"


def get_client_ip(request):
    """
    استخراج عنوان الـ IP الحقيقي للجهاز حتى عند العمل خلف Proxy أو Cloudflare أو Nginx
    """
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_activity(
    request=None,
    module='other',
    action_type='other',
    description='',
    severity='info',
    extra_data=None,
    user=None,
    tenant=None
):
    """
    تسجيل حركة فوري ورقابي داخل سجل النشاطات (AuditLog).
    دالة آمنة تماماً، لا تتسبب في أي إيقاف لعمليات النظام إذا حدث أي خطأ أثناء الحفظ.
    """
    try:
        from dashboard.models import AuditLog

        req_user = None
        if user:
            req_user = user
        elif request and hasattr(request, 'user') and request.user.is_authenticated:
            req_user = request.user

        user_display = "النظام التلقائي"
        user_email = ""
        if req_user:
            user_display = req_user.get_full_name() or req_user.username
            user_email = req_user.email or ""

        ip_address = get_client_ip(request) if request else None
        user_agent_str = request.META.get('HTTP_USER_AGENT', '') if request else ''
        device_info = parse_device_info(user_agent_str) if user_agent_str else 'سيرفر داخلي'

        req_tenant = tenant
        if not req_tenant and request:
            req_tenant = getattr(request, 'tenant', None)

        return AuditLog.objects.create(
            user=req_user,
            user_display=user_display,
            user_email=user_email,
            tenant=req_tenant,
            module=module,
            action_type=action_type,
            severity=severity,
            description=description,
            ip_address=ip_address,
            device_info=device_info,
            user_agent=user_agent_str[:500] if user_agent_str else '',
            extra_data=extra_data,
        )
    except Exception as e:
        logger.error(f"[AUDIT LOG ERROR] Failed to record activity: {str(e)}")
        return None
