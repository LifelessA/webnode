# core/validators.py
import html
import re

# ─────────────────────────────────────
# Exception
# ─────────────────────────────────────

class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

# ─────────────────────────────────────
# Individual Validators
# ─────────────────────────────────────

def validate_int(
    value,
    field_name: str,
    min_val: int = None,
    max_val: int = None,
    required: bool = True
) -> int:
    """
    Validate and return an integer value.
    
    Raises ValidationError if:
    - required=True and value is None/empty
    - value cannot be converted to int
    - value < min_val
    - value > max_val
    
    Returns int on success.
    """
    if value is None or str(value).strip() == '':
        if required:
            raise ValidationError(field_name, f"{field_name} is required")
        return None
    
    try:
        result = int(str(value).strip())
    except (ValueError, TypeError):
        raise ValidationError(field_name, f"{field_name} must be a number")
    
    if min_val is not None and result < min_val:
        raise ValidationError(field_name, f"{field_name} must be at least {min_val}")
    
    if max_val is not None and result > max_val:
        raise ValidationError(field_name, f"{field_name} must be at most {max_val}")
    
    return result


def validate_str(
    value,
    field_name: str,
    min_length: int = 0,
    max_length: int = 255,
    required: bool = True,
    strip: bool = True
) -> str:
    """
    Validate and return a safe string.
    
    - Strips whitespace if strip=True
    - HTML escapes the value (XSS prevention)
    - Raises ValidationError if:
      * required=True and empty
      * length < min_length
      * length > max_length
    
    Returns html-escaped string on success.
    """
    if value is None:
        if required:
            raise ValidationError(field_name, f"{field_name} is required")
        return ''
    
    value = str(value)
    if strip:
        value = value.strip()
    
    if required and len(value) == 0:
        raise ValidationError(field_name, f"{field_name} is required")
    
    if len(value) < min_length:
        raise ValidationError(field_name, f"{field_name} must be at least {min_length} characters")
    
    if len(value) > max_length:
        raise ValidationError(field_name, f"{field_name} must be at most {max_length} characters")
    
    # XSS prevention — always escape
    return html.escape(value)


def validate_email(
    value,
    field_name: str = 'email',
    required: bool = True
) -> str:
    """
    Validate email format.
    
    - Basic format check: x@x.x
    - Max length 254 chars (RFC 5321)
    - Returns lowercased, stripped, html-escaped email
    
    Raises ValidationError if invalid.
    """
    value = validate_str(
        value,
        field_name,
        max_length=254,
        required=required
    )
    
    if not value and not required:
        return ''
    
    # Basic email pattern
    pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    if not re.match(pattern, html.unescape(value)):
        raise ValidationError(field_name, "Invalid email address")
    
    return value.lower()


# ─────────────────────────────────────
# Bulk Form Validator
# ─────────────────────────────────────

def validate_form(
    request,
    rules: dict
) -> tuple[dict, list]:
    """
    Validate multiple form fields at once.
    
    rules format:
    {
        'field_name': {
            'type': 'int' | 'str' | 'email',
            'required': True | False,
            'min': value,      (int: min_val, str: min_length)
            'max': value,      (int: max_val, str: max_length)
        }
    }
    
    Returns:
        (cleaned_data dict, errors list)
    """
    cleaned = {}
    errors = []
    
    for field, rule in rules.items():
        # Handle both Mock objects and real framework requests
        value = request.get_param(field) if hasattr(request, 'get_param') else request.get(field)
        field_type = rule.get('type', 'str')
        required = rule.get('required', True)
        
        try:
            if field_type == 'int':
                cleaned[field] = validate_int(
                    value,
                    field,
                    min_val=rule.get('min'),
                    max_val=rule.get('max'),
                    required=required
                )
            elif field_type == 'email':
                cleaned[field] = validate_email(
                    value,
                    field,
                    required=required
                )
            else:  # str default
                cleaned[field] = validate_str(
                    value,
                    field,
                    min_length=rule.get('min', 0),
                    max_length=rule.get('max', 255),
                    required=required
                )
        except ValidationError as e:
            errors.append(e.message)
    
    return cleaned, errors


# ─────────────────────────────────────
# Safe Helpers (no exception versions)
# ─────────────────────────────────────

def safe_int(
    value,
    default: int = 0,
    min_val: int = None,
    max_val: int = None
) -> int:
    """
    Safely convert to int — returns default instead of raising.
    """
    try:
        result = int(str(value).strip())
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return default
        return result
    except (ValueError, TypeError, AttributeError):
        return default


def safe_str(
    value,
    default: str = '',
    max_length: int = 255
) -> str:
    """
    Safely get string value — returns default instead of raising.
    HTML escaped for XSS prevention.
    """
    if value is None:
        return default
    try:
        result = html.escape(str(value).strip())
        if len(result) > max_length:
            return default
        return result
    except Exception:
        return default
