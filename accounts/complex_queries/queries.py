def join_queries(model, select_related, prefetch_related):
    # Initialize the queryset for the requested user's role model.
    queryset = model.objects
    
    # Apply select_related and prefetch_related as needed for the requested user's account.
    if select_related:
        queryset = queryset.select_related(select_related)
    if prefetch_related:
        queryset = queryset.prefetch_related(*prefetch_related.split(', '))

    return queryset