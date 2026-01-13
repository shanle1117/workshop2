# Validate response before caching
validated_response = validate_response(answer, intent)

# Build response data with validated response
response_data = {
    'response': validated_response,
    # ... other fields
}

# Cache validated response
cache.set(cache_key, response_data, timeout=cache_timeout)