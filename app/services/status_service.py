"""Status management service"""
from app.models.peripheral import Peripheral
from app.models.status_history import StatusHistory
from app.services.alert_service import AlertService
from app.utils.constants import PERIPHERAL_STATUSES, ALERT_TYPES
from app.utils.helpers import get_current_timestamp


class StatusService:
    """Service for managing peripheral statuses"""
    
    @staticmethod
    def update_status(peripheral_id, new_status, reason=None, updated_by=None):
        """Update peripheral status with validation and alert creation"""
        # Get current peripheral
        peripheral = Peripheral.get_by_id(peripheral_id)
        if not peripheral:
            raise ValueError("Peripheral not found")
        
        old_status = peripheral.get('status', '').lower() if peripheral.get('status') else None
        new_status_lower = new_status.lower()
        
        # Validate status transition
        if not Peripheral.validate_status_transition(old_status, new_status_lower):
            raise ValueError(f"Invalid status transition from '{old_status}' to '{new_status_lower}'")
        
        # Update status
        Peripheral.update_status_manual(peripheral_id, new_status_lower, reason, updated_by)
        
        # Create alert if status is missing, faulty, or replaced
        if new_status_lower in ALERT_TYPES:
            AlertService.create_alert(
                peripheral.get('serial_number', '') or peripheral.get('unique_id', ''),
                new_status_lower,
                get_current_timestamp(),
                peripheral.get('assigned_pc', ''),
                peripheral.get('lab_id', ''),
                'manual_status_change',
                peripheral.get('name', ''),
                updated_by or 'system'
            )
        
        return True
    
    @staticmethod
    def get_status_history(peripheral_id):
        """Get status history for a peripheral"""
        return StatusHistory.get_by_peripheral(peripheral_id)
    
    @staticmethod
    def bulk_update_status(peripheral_ids, new_status, reason=None, updated_by=None):
        """Bulk update status for multiple peripherals"""
        results = []
        errors = []
        
        for peripheral_id in peripheral_ids:
            try:
                StatusService.update_status(peripheral_id, new_status, reason, updated_by)
                results.append(peripheral_id)
            except Exception as e:
                errors.append({'peripheral_id': peripheral_id, 'error': str(e)})
        
        return {
            'success': results,
            'errors': errors,
            'total': len(peripheral_ids),
            'success_count': len(results),
            'error_count': len(errors)
        }

