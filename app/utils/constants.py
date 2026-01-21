"""Application constants"""
# Peripheral status values
PERIPHERAL_STATUSES = {
    'connected': 'Connected',
    'unplugged': 'Unplugged',
    'missing': 'Missing',
    'faulty': 'Faulty',
    'replaced': 'Replaced'
}

# Valid status transitions
STATUS_TRANSITIONS = {
    'connected': ['unplugged', 'faulty', 'replaced'],
    'unplugged': ['connected', 'missing', 'faulty'],
    'missing': ['connected', 'replaced'],
    'faulty': ['connected', 'replaced'],
    'replaced': ['connected']
}

# Device status values
DEVICE_STATUSES = {
    'active': 'Active',
    'maintenance': 'Maintenance',
    'retired': 'Retired',
    'faulty': 'Faulty'
}

# Alert types
ALERT_TYPES = ['missing', 'faulty', 'replaced']

# User roles
USER_ROLES = {
    'admin': 'Administrator',
    'student': 'Student'
}

# User statuses
USER_STATUSES = {
    'pending': 'Pending',
    'active': 'Active',
    'suspended': 'Suspended',
    'inactive': 'Inactive'
}


