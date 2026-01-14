"""USB device detection using Windows SetupAPI (SetupDi* functions)
This module uses native Windows APIs for faster and more reliable device detection:
- SetupDiGetClassDevs: Get device class list
- SetupDiEnumDeviceInfo: Enumerate devices
- SetupDiGetDeviceRegistryProperty: Get device properties (name, manufacturer, etc.)
- SetupDiGetDeviceInstanceId: Get device instance ID (VID/PID)
Compatible with Windows 7/8/10/11.
"""
import sys
import os
import platform
import re

# Check if running on Windows
IS_WINDOWS = platform.system() == 'Windows'

# Try to import pywin32 for Windows APIs
WIN32_AVAILABLE = False
if IS_WINDOWS:
    try:
        import win32api
        import win32con
        import win32file
        from win32com.shell import shell
        import win32gui
        WIN32_AVAILABLE = True
    except ImportError:
        try:
            # Try alternative imports
            import win32api
            WIN32_AVAILABLE = True
        except ImportError:
            WIN32_AVAILABLE = False
            print("Warning: pywin32 not available. Install with: pip install pywin32")

# SetupAPI constants (from setupapi.h)
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010
SPDRP_DEVICEDESC = 0x00000000
SPDRP_HARDWAREID = 0x00000001
SPDRP_COMPATIBLEIDS = 0x00000002
SPDRP_MFG = 0x0000000B
SPDRP_FRIENDLYNAME = 0x0000000C
SPDRP_CLASS = 0x00000007
SPDRP_CLASSGUID = 0x00000008
SPDRP_ENUMERATOR_NAME = 0x00000016
SPDRP_PHYSICAL_DEVICE_OBJECT_NAME = 0x0000000E

# Device interface GUIDs
GUID_DEVINTERFACE_USB_DEVICE = "{A5DCBF10-6530-11D2-901F-00C04FB951ED}"
GUID_DEVINTERFACE_HID = "{4D1E55B2-F16F-11CF-88CB-001111000030}"


def extract_vid_pid_instance(device_instance_id):
    """Extract VID, PID, and instance number from Windows device instance ID
    
    Device Instance ID format examples:
    - USB\\VID_046D&PID_C077\\5&12345678&0&1
    - HID\\VID_046D&PID_C077\\6&ABCDEF12&0&0
    
    Returns: (vid, pid, instance_number)
    """
    try:
        if not device_instance_id:
            return "UNKNOWN", "UNKNOWN", "UNKNOWN"
        
        # Extract VID and PID using regex
        vid_match = re.search(r'VID_([0-9A-F]{4})', device_instance_id, re.IGNORECASE)
        pid_match = re.search(r'PID_([0-9A-F]{4})', device_instance_id, re.IGNORECASE)
        
        vid = vid_match.group(1).upper() if vid_match else "UNKNOWN"
        pid = pid_match.group(1).upper() if pid_match else "UNKNOWN"
        
        # Extract instance number - it's usually the last part after the last backslash
        parts = device_instance_id.split("\\")
        if len(parts) >= 3:
            instance_part = parts[-1]
            # Use the instance part as-is, but limit length
            instance_number = instance_part.replace("&", "_").replace(" ", "_")
            if len(instance_number) > 30:
                instance_number = instance_number[:30]
        elif len(parts) == 2:
            # Fallback: use a hash of the full device_id for uniqueness
            instance_number = str(abs(hash(device_instance_id)) % 10000)
        else:
            instance_number = str(abs(hash(device_instance_id)) % 10000)
        
        if not instance_number or instance_number == "":
            instance_number = "0000"
        
        return vid, pid, instance_number
    except Exception as e:
        print(f"Error extracting VID/PID/Instance from {device_instance_id}: {e}")
        return "UNKNOWN", "UNKNOWN", "UNKNOWN"


def is_built_in_device(name, manufacturer, pnp_class, device_id):
    """Check if a device is a built-in/internal device that should be filtered out"""
    name_lower = (name or "").lower()
    manufacturer_lower = (manufacturer or "").lower()
    cls = (pnp_class or "").lower()
    dev_id = (device_id or "").lower()
    
    # Filter out built-in/internal devices
    built_in_keywords = [
        # Internal Bluetooth adapters
        "intel", "wireless bluetooth", "bluetooth adapter",
        # Built-in touchpads/trackpads (must be comprehensive)
        "synaptics", "touchpad", "touch pad", "pointstyk", "stykfhid", 
        "hid-compliant touch pad", "hid-compliant touchpad",
        # Internal system controllers
        "system controller", "vendor-defined device", "consumer control",
        "hid-compliant vendor-defined device", "hid-compliant system controller",
        # Microsoft internal devices
        "microsoft input configuration", "wireless radio controls",
        # Unknown internal devices
        "vid_unknown", "pid_unknown",
        # Internal USB hubs
        "usb root hub", "usb hub",
        # Internal audio (keep external audio devices)
        "realtek", "high definition audio"
    ]
    
    # Check for headphones/headsets - these should NOT be filtered
    if "headphone" in name_lower or "headset" in name_lower:
        # Don't filter external audio devices
        if "realtek" in name_lower or "high definition audio" in name_lower:
            return False
    
    # Check if device matches built-in patterns
    for keyword in built_in_keywords:
        if keyword and keyword in name_lower:
            return True
        if keyword and keyword in manufacturer_lower:
            return True
    
    # Filter out devices with UNKNOWN VID/PID (usually internal)
    if "vid_unknown" in dev_id or "pid_unknown" in dev_id:
        return True
    
    # Filter out internal HID devices that aren't keyboards/mice
    if cls == "hidclass":
        # Filter touchpads (even if they're HID)
        if "touchpad" in name_lower or "touch pad" in name_lower:
            return True
        
        # Filter vendor-defined and system controllers
        if "vendor-defined" in name_lower or "system controller" in name_lower:
            return True
        
        # Filter consumer control devices (usually built-in)
        if "consumer control" in name_lower:
            return True
        
        # Filter built-in keyboards/mice - check for patterns that indicate built-in
        # Built-in keyboards often have "HID Keyboard Device" without a brand name
        # or are part of composite devices
        if "keyboard" in name_lower:
            # If it's a generic "HID Keyboard Device" without a specific brand/manufacturer
            # and has UNKNOWN VID/PID, it's likely built-in
            if ("hid keyboard device" in name_lower or "hid-compliant keyboard" in name_lower):
                if "vid_unknown" in dev_id or "pid_unknown" in dev_id:
                    return True
                # If manufacturer is empty or generic, likely built-in
                if not manufacturer or manufacturer.lower() in ["", "standard", "generic"]:
                    # Check if it's part of a composite device (laptop keyboard)
                    if "composite" in name_lower or "composite device" in manufacturer_lower:
                        return True
        
        # Filter built-in mice - similar logic
        if "mouse" in name_lower:
            if ("hid-compliant mouse" in name_lower or "hid mouse device" in name_lower):
                if "vid_unknown" in dev_id or "pid_unknown" in dev_id:
                    return True
                if not manufacturer or manufacturer.lower() in ["", "standard", "generic"]:
                    return True
    
    return False


def get_device_type(name, pnp_class, device_id):
    """Determine device type from name, PNP class, and device ID"""
    name_lower = (name or "").lower()
    cls = (pnp_class or "").lower()
    dev_id = (device_id or "").lower()

    # KEYBOARD
    if ("keyboard" in name_lower or 
        "keyboard" in dev_id or 
        "keyboard" in cls or
        "hid keyboard" in name_lower):
        return "Keyboard"

    # MOUSE
    if "mouse" in name_lower or "mouse" in dev_id:
        return "Mouse"

    # FLASH DRIVE
    if "usbstor" in dev_id or "disk" in name_lower or "removable" in name_lower:
        return "Flash Drive"

    # PRINTER
    if "printer" in name_lower:
        return "Printer"

    # CAMERA / SCANNER
    if "camera" in name_lower or cls == "image" or "scanner" in name_lower:
        return "Camera / Scanner"

    # AUDIO (external headphones/headsets only)
    if ("headphone" in name_lower or "headset" in name_lower or 
        ("audio" in name_lower and "headphone" in name_lower)):
        return "Audio Device"
    
    # Check PNP class
    if cls == "keyboard" or cls == "hidclass":
        if "hid" in dev_id:
            return "Keyboard"
    
    return "Unknown Device"


def get_connected_devices():
    """Get all currently connected USB/HID devices using Windows SetupAPI
    
    Uses:
    - SetupDiGetClassDevs: Get device class list
    - SetupDiEnumDeviceInfo: Enumerate devices
    - SetupDiGetDeviceRegistryProperty: Get device properties
    - SetupDiGetDeviceInstanceId: Get device instance ID
    
    Returns:
        list: List of detected device dictionaries with type, vendor, product, etc.
    """
    if not IS_WINDOWS:
        return []
    
    if not WIN32_AVAILABLE:
        return []
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # Define GUID structure manually (not available in wintypes)
        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8)
            ]
        
        # Load setupapi.dll
        setupapi = ctypes.windll.setupapi
        
        # Load ole32.dll for CLSIDFromString
        ole32 = ctypes.windll.ole32
        
        # Define CLSIDFromString function
        CLSIDFromString = ole32.CLSIDFromString
        # Use c_void_p for GUID pointer to avoid type identity issues
        CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p]
        CLSIDFromString.restype = ctypes.c_long
        
        # Define function signatures
        SetupDiGetClassDevs = setupapi.SetupDiGetClassDevsW
        # Use c_void_p for GUID pointer to avoid type identity issues
        SetupDiGetClassDevs.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
        SetupDiGetClassDevs.restype = wintypes.HANDLE
        
        # Define SP_DEVINFO_DATA structure first (needed for SetupDiEnumDeviceInfo)
        class SP_DEVINFO_DATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("ClassGuid", GUID),
                ("DevInst", wintypes.DWORD),
                ("Reserved", ctypes.POINTER(wintypes.ULONG))
            ]
        
        # Create proper pointer type alias
        LP_SP_DEVINFO_DATA = ctypes.POINTER(SP_DEVINFO_DATA)
        
        SetupDiEnumDeviceInfo = setupapi.SetupDiEnumDeviceInfo
        # Specify argtypes for HANDLE/DWORD but use c_void_p for structure pointer
        # This allows byref() to work while ensuring proper HANDLE conversion
        SetupDiEnumDeviceInfo.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p]
        SetupDiEnumDeviceInfo.restype = wintypes.BOOL
        
        SetupDiGetDeviceRegistryProperty = setupapi.SetupDiGetDeviceRegistryPropertyW
        # Specify argtypes for HANDLE/DWORD but use c_void_p for structure pointer
        SetupDiGetDeviceRegistryProperty.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.BYTE),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)
        ]
        SetupDiGetDeviceRegistryProperty.restype = wintypes.BOOL
        
        SetupDiGetDeviceInstanceId = setupapi.SetupDiGetDeviceInstanceIdW
        # Specify argtypes for HANDLE/DWORD but use c_void_p for structure pointer
        SetupDiGetDeviceInstanceId.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.WCHAR),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)
        ]
        SetupDiGetDeviceInstanceId.restype = wintypes.BOOL
        
        SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList
        SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
        SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
        
        devices = {}
        grouped = {}
        
        # Get USB devices
        usb_guid = GUID()
        usb_guid_string = GUID_DEVINTERFACE_USB_DEVICE
        CLSIDFromString(usb_guid_string, ctypes.cast(ctypes.byref(usb_guid), ctypes.c_void_p))
        
        device_info_set = SetupDiGetClassDevs(
            ctypes.cast(ctypes.byref(usb_guid), ctypes.c_void_p),
            None,
            None,
            DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
        )
        
        if device_info_set != wintypes.HANDLE(-1).value:
            index = 0
            
            while True:
                # Create a new structure for each iteration
                dev_info_data = SP_DEVINFO_DATA()
                dev_info_data.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
                
                # Call the function - use byref() and cast to c_void_p for compatibility
                # This ensures proper HANDLE conversion while maintaining output parameter behavior
                result = SetupDiEnumDeviceInfo(
                    device_info_set, 
                    index, 
                    ctypes.cast(ctypes.byref(dev_info_data), ctypes.c_void_p)
                )
                if not result:
                    break
                
                try:
                    # Get device instance ID
                    instance_id_buffer = ctypes.create_unicode_buffer(260)
                    instance_id_size = wintypes.DWORD(260)
                    
                    if SetupDiGetDeviceInstanceId(
                        device_info_set,
                        ctypes.cast(ctypes.byref(dev_info_data), ctypes.c_void_p),
                        instance_id_buffer,
                        260,
                        ctypes.byref(instance_id_size)
                    ):
                        device_instance_id = instance_id_buffer.value
                        
                        # Filter for USB and HID devices only
                        if not device_instance_id.startswith(("USB\\", "HID\\")):
                            index += 1
                            continue
                        
                        # Get device properties
                        name = ""
                        manufacturer = ""
                        description = ""
                        pnp_class = ""
                        
                        # Helper function to safely get registry property
                        def get_registry_property(property_type):
                            prop_buffer = (ctypes.c_char * 2048)()
                            prop_size = wintypes.DWORD(0)
                            if SetupDiGetDeviceRegistryProperty(
                                device_info_set,
                                ctypes.cast(ctypes.byref(dev_info_data), ctypes.c_void_p),
                                property_type,
                                None,
                                ctypes.cast(prop_buffer, ctypes.POINTER(wintypes.BYTE)),
                                2048,
                                ctypes.byref(prop_size)
                            ) and prop_size.value > 0:
                                try:
                                    # Only decode the actual data size, ensure it's even (UTF-16 needs pairs)
                                    data_size = prop_size.value
                                    if data_size % 2 != 0:
                                        data_size -= 1  # Make it even
                                    if data_size > 0:
                                        data_bytes = bytes(prop_buffer[:data_size])
                                        return data_bytes.decode('utf-16-le', errors='ignore').rstrip('\x00')
                                except:
                                    pass
                            return ""
                        
                        # Get device properties safely
                        name = get_registry_property(SPDRP_DEVICEDESC)
                        manufacturer = get_registry_property(SPDRP_MFG)
                        description = get_registry_property(SPDRP_FRIENDLYNAME)
                        pnp_class = get_registry_property(SPDRP_CLASS)
                        
                        # Extract VID, PID, instance
                        vid, pid, instance = extract_vid_pid_instance(device_instance_id)
                        key = f"{vid}_{pid}_{instance}"
                        
                        # Filter out built-in devices BEFORE processing
                        if is_built_in_device(name, manufacturer, pnp_class, device_instance_id):
                            index += 1
                            continue
                        
                        # Determine device type
                        dtype = get_device_type(name, pnp_class, device_instance_id)
                        
                        # Skip "Unknown Device" types that are likely built-in
                        if dtype == "Unknown Device":
                            name_lower = (name or "").lower()
                            # Additional check: if it's an unknown device with internal characteristics, skip it
                            if "vendor-defined" in name_lower or "system controller" in name_lower:
                                index += 1
                                continue
                        
                        # Group devices by VID_PID_INSTANCE
                        if key not in grouped:
                            grouped[key] = {
                                "vid": vid,
                                "pid": pid,
                                "types": set(),
                                "instance": instance,
                                "name": name,
                                "manufacturer": manufacturer,
                                "description": description,
                                "pnp_class": pnp_class
                            }
                        
                        grouped[key]["types"].add(dtype)
                        
                except Exception as e:
                    print(f"Error processing device at index {index}: {e}")
                
                index += 1
            
            SetupDiDestroyDeviceInfoList(device_info_set)
        
        # Also get HID devices
        hid_guid = GUID()
        hid_guid_string = GUID_DEVINTERFACE_HID
        CLSIDFromString(hid_guid_string, ctypes.cast(ctypes.byref(hid_guid), ctypes.c_void_p))
        
        device_info_set = SetupDiGetClassDevs(
            ctypes.cast(ctypes.byref(hid_guid), ctypes.c_void_p),
            None,
            None,
            DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
        )
        
        if device_info_set != wintypes.HANDLE(-1).value:
            index = 0
            
            while True:
                # Create a new structure for each iteration
                dev_info_data = SP_DEVINFO_DATA()
                dev_info_data.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
                
                # Call the function - use byref() and cast to c_void_p for compatibility
                # This ensures proper HANDLE conversion while maintaining output parameter behavior
                result = SetupDiEnumDeviceInfo(
                    device_info_set, 
                    index, 
                    ctypes.cast(ctypes.byref(dev_info_data), ctypes.c_void_p)
                )
                if not result:
                    break
                
                try:
                    # Get device instance ID
                    instance_id_buffer = ctypes.create_unicode_buffer(260)
                    instance_id_size = wintypes.DWORD(260)
                    
                    if SetupDiGetDeviceInstanceId(
                        device_info_set,
                        ctypes.cast(ctypes.byref(dev_info_data), ctypes.c_void_p),
                        instance_id_buffer,
                        260,
                        ctypes.byref(instance_id_size)
                    ):
                        device_instance_id = instance_id_buffer.value
                        
                        # Filter for HID devices only (already processed USB)
                        if not device_instance_id.startswith("HID\\"):
                            index += 1
                            continue
                        
                        # Skip if already processed
                        vid, pid, instance = extract_vid_pid_instance(device_instance_id)
                        key = f"{vid}_{pid}_{instance}"
                        if key in grouped:
                            index += 1
                            continue
                        
                        # Get device properties
                        name = ""
                        manufacturer = ""
                        description = ""
                        pnp_class = ""
                        
                        # Helper function to safely get registry property (reuse same function)
                        def get_registry_property_hid(property_type):
                            prop_buffer = (ctypes.c_char * 2048)()
                            prop_size = wintypes.DWORD(0)
                            if SetupDiGetDeviceRegistryProperty(
                                device_info_set,
                                ctypes.cast(ctypes.byref(dev_info_data), ctypes.c_void_p),
                                property_type,
                                None,
                                ctypes.cast(prop_buffer, ctypes.POINTER(wintypes.BYTE)),
                                2048,
                                ctypes.byref(prop_size)
                            ) and prop_size.value > 0:
                                try:
                                    # Only decode the actual data size, ensure it's even (UTF-16 needs pairs)
                                    data_size = prop_size.value
                                    if data_size % 2 != 0:
                                        data_size -= 1  # Make it even
                                    if data_size > 0:
                                        data_bytes = bytes(prop_buffer[:data_size])
                                        return data_bytes.decode('utf-16-le', errors='ignore').rstrip('\x00')
                                except:
                                    pass
                            return ""
                        
                        # Get device properties safely
                        name = get_registry_property_hid(SPDRP_DEVICEDESC)
                        manufacturer = get_registry_property_hid(SPDRP_MFG)
                        description = get_registry_property_hid(SPDRP_FRIENDLYNAME)
                        pnp_class = get_registry_property_hid(SPDRP_CLASS)
                        
                        # Filter out built-in devices BEFORE processing
                        if is_built_in_device(name, manufacturer, pnp_class, device_instance_id):
                            index += 1
                            continue
                        
                        # Determine device type
                        dtype = get_device_type(name, pnp_class, device_instance_id)
                        
                        # Skip "Unknown Device" types that are likely built-in
                        if dtype == "Unknown Device":
                            name_lower = (name or "").lower()
                            # Additional check: if it's an unknown device with internal characteristics, skip it
                            if "vendor-defined" in name_lower or "system controller" in name_lower:
                                index += 1
                                continue
                        
                        # Group devices
                        if key not in grouped:
                            grouped[key] = {
                                "vid": vid,
                                "pid": pid,
                                "types": set(),
                                "instance": instance,
                                "name": name,
                                "manufacturer": manufacturer,
                                "description": description,
                                "pnp_class": pnp_class
                            }
                        
                        grouped[key]["types"].add(dtype)
                        
                except Exception as e:
                    print(f"Error processing HID device at index {index}: {e}")
                
                index += 1
            
            SetupDiDestroyDeviceInfoList(device_info_set)
        
        # Process grouped devices and assign final type
        result = []
        for key, data in grouped.items():
            # Final filter check - exclude built-in devices that might have slipped through
            if is_built_in_device(data["name"], data["manufacturer"], data["pnp_class"], key):
                continue
            
            # Priority logic
            if "Keyboard" in data["types"]:
                final_type = "Keyboard"
            elif "Mouse" in data["types"]:
                final_type = "Mouse"
            elif "Flash Drive" in data["types"]:
                final_type = "Flash Drive"
            elif "Camera / Scanner" in data["types"]:
                final_type = "Camera / Scanner"
            elif "Printer" in data["types"]:
                final_type = "Printer"
            elif "Audio Device" in data["types"]:
                final_type = "Audio Device"
            else:
                # Skip unknown devices that are likely built-in
                final_type = "Unknown Device"
                # Additional check for unknown devices
                name_lower = (data["name"] or "").lower()
                if "vendor-defined" in name_lower or "system controller" in name_lower:
                    continue

            result.append({
                "type": final_type,
                "vendor": data["vid"],
                "product": data["pid"],
                "unique_id": f"VID_{data['vid']}_PID_{data['pid']}_INST_{data['instance']}",
                "name": data["name"],
                "manufacturer": data["manufacturer"],
                "description": data["description"],
                "pnp_class": data["pnp_class"],
                "device_key": key
            })

        return result
        
    except Exception as e:
        print(f"Error detecting devices via Windows SetupAPI: {e}")
        import traceback
        traceback.print_exc()
        return []


def detect_new_device(previous_device_keys):
    """Detect newly plugged-in devices by comparing with previous device list
    
    Args:
        previous_device_keys: Set or list of device keys from previous detection
        
    Returns:
        tuple: (new_devices_list, current_device_keys_set)
    """
    if not IS_WINDOWS or not WIN32_AVAILABLE:
        return [], set()
    
    try:
        # Get current devices
        current_devices = get_connected_devices()
        
        if not isinstance(current_devices, list):
            current_devices = []
        
        current_keys = {dev.get("device_key", "") for dev in current_devices if dev.get("device_key")}
        
        # Convert previous_device_keys to set if it's not already
        if previous_device_keys is None:
            previous_keys_set = set()
        elif isinstance(previous_device_keys, set):
            previous_keys_set = previous_device_keys
        elif isinstance(previous_device_keys, (list, tuple)):
            previous_keys_set = set(previous_device_keys)
        else:
            previous_keys_set = set()
        
        # Find devices that are in current list but not in previous list
        new_keys = current_keys - previous_keys_set
        new_devices = [dev for dev in current_devices if dev.get("device_key") in new_keys]
        
        return new_devices, current_keys
    except Exception as e:
        print(f"Error detecting new device: {e}")
        import traceback
        traceback.print_exc()
        return [], set()


def detect_disconnected_devices(previous_device_keys, registered_unique_ids):
    """Detect devices that were previously connected but are now disconnected
    
    Args:
        previous_device_keys: Set or list of device keys from previous detection
        registered_unique_ids: List of unique IDs from registered peripherals
        
    Returns:
        list: List of unique IDs that are disconnected
    """
    if not IS_WINDOWS or not WIN32_AVAILABLE:
        return []
    
    try:
        # Get current devices
        current_devices = get_connected_devices()
        
        if not isinstance(current_devices, list):
            current_devices = []
        
        # Get unique IDs of currently connected devices
        current_unique_ids = {dev.get("unique_id", "") for dev in current_devices if dev.get("unique_id")}
        
        # Convert registered_unique_ids to set
        if registered_unique_ids is None:
            registered_set = set()
        elif isinstance(registered_unique_ids, (list, tuple)):
            registered_set = set(registered_unique_ids)
        elif isinstance(registered_unique_ids, set):
            registered_set = registered_unique_ids
        else:
            registered_set = set()
        
        # Find registered devices that are not currently connected
        disconnected_ids = registered_set - current_unique_ids
        
        return list(disconnected_ids)
    except Exception as e:
        print(f"Error detecting disconnected devices: {e}")
        import traceback
        traceback.print_exc()
        return []


def check_windows_compatibility():
    """Check if Windows device detection is available and working
    
    Returns:
        dict: Compatibility status with details
    """
    result = {
        "is_windows": IS_WINDOWS,
        "win32_available": WIN32_AVAILABLE,
        "compatible": False,
        "message": "",
        "platform": platform.system(),
        "platform_version": platform.version()
    }
    
    if not IS_WINDOWS:
        result["message"] = "Device detection requires Windows. This feature uses Windows SetupAPI which is Windows-specific."
        return result
    
    if not WIN32_AVAILABLE:
        result["message"] = "pywin32 module not available. Install with: pip install pywin32"
        return result
    
    # Try to detect devices to check if it's working
    try:
        test_devices = get_connected_devices()
        result["compatible"] = True
        result["message"] = f"Windows device detection is ready. Using Windows SetupAPI. Found {len(test_devices)} device(s)."
        result["device_count"] = len(test_devices)
    except Exception as e:
        result["message"] = f"Windows SetupAPI is available but not working: {str(e)}"
        result["error"] = str(e)
    
    return result

# For backward compatibility
WMI_AVAILABLE = False  # We're not using WMI anymore
PYTHONCOM_AVAILABLE = WIN32_AVAILABLE
