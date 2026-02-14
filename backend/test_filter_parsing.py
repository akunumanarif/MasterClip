"""
Test filter parsing logic
"""
test_filters = [
    'eq=contrast=1.15:brightness=0.03:saturation=1.2:gamma=1.1',
    'hue=s=0',
    'eq=contrast=1.35:brightness=0.03:gamma=0.95'
]

for filter_str in test_filters:
    print(f"\nTesting: {filter_str}")
    
    if '=' in filter_str:
        parts = filter_str.split('=', 1)
        filter_name = parts[0]
        
        params = {}
        if len(parts) > 1 and parts[1]:
            param_str = parts[1]
            for param in param_str.split(':'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    try:
                        params[key] = float(value)
                    except ValueError:
                        params[key] = value
        
        print(f"  Filter: {filter_name}")
        print(f"  Params: {params}")
        print(f"  Call: video.filter('{filter_name}', {', '.join(f'{k}={v}' for k, v in params.items())})")
    else:
        print(f"  Simple filter: {filter_str}")

print("\n✅ All filters parsed successfully!")
