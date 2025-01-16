from user_agents import parse  # Using the `user_agents` package to parse the user-agent string


def generate_device_details(request):
    # Extract the user-agent string from the request headers
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Parse the user-agent string using the user_agents package
    user_agent_data = parse(user_agent)
    
    # Initialize device information dictionary
    browser_info = {
        'device_type': 'Unknown',
        'os': 'Unknown',
        'os_version': 'Unknown',
        'browser': 'Unknown',
        'browser_version': 'Unknown',
        'language': request.META.get('HTTP_ACCEPT_LANGUAGE', 'Unknown'),
        'time_zone': request.META.get('HTTP_TIMEZONE', 'Unknown'),  # This would need to be sent from the frontend
    }

    # Detect the device type (Mobile, Desktop, Tablet, TV)
    if user_agent_data.is_mobile:
        browser_info['device_type'] = 'Mobile'
    elif user_agent_data.is_tablet:
        browser_info['device_type'] = 'Tablet'
    elif user_agent_data.is_pc:
        browser_info['device_type'] = 'PC'
    elif user_agent_data.is_tv:
        browser_info['device_type'] = 'TV'

    # Detect OS and version (e.g., Android, iOS, Windows, MacOS)
    if user_agent_data.os.family:
        browser_info['os'] = user_agent_data.os.family
        browser_info['os_version'] = user_agent_data.os.version_string

    # Detect browser and version (e.g., Chrome, Firefox, Safari)
    if user_agent_data.browser.family:
        browser_info['browser'] = user_agent_data.browser.family
        browser_info['browser_version'] = user_agent_data.browser.version_string

    return browser_info
