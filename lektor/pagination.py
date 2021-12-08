class Pagination:
    def __init__(self, record, pagination_config):
        #: the pagination config
        self.config = pagination_config
        #: the current page's record
        self.current = record
        #: the current page number (1 indexed)
        self.page = record.page_num
        #: the number of items to be displayed on a page.
        self.per_page = pagination_config.per_page
        #: the total number of items matching the query
        self.total = pagination_config.count_total_items(record)

    @property
    def items(self):
        """The children for this page."""
        return self.config.slice_query_for_page(self.current, self.page)

    @property
    def pages(self):
        """The total number of pages."""
        pages = (self.total + self.per_page - 1) // self.per_page
        # Even when there are no children, we want at least one page
        return max(pages, 1)

    @property
    def prev_num(self):
        """The page number of the previous page."""
        if self.page > 1:
            return self.page - 1
        return None

    @property
    def has_prev(self):
        """True if a previous page exists."""
        return self.page > 1

    @property
    def prev(self):
        """The record for the previous page."""
        if not self.has_prev:
            return None
        return self.config.get_record_for_page(self.current, self.page - 1)

    @property
    def has_next(self):
        """True if a following page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """The page number of the following page."""
        if self.page < self.pages:
            return self.page + 1
        return None

    @property
    def next(self):
        """The record for the following page."""
        if not self.has_next:
            return None
        return self.config.get_record_for_page(self.current, self.page + 1)

    def for_page(self, page):
        """Returns the record for a specific page."""
        if 1 <= page <= self.pages:
            return self.config.get_record_for_page(self.current, page)
        return None

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        """Iterate over the page numbers in the pagination, with elision.

        In the general case, this returns the concatenation of three ranges:

            1. A range (always starting at page one) at the beginning
               of the page number sequence.  The length of the this
               range is specified by the ``left_edge`` argument (which
               may be zero).

            2. A range around the current page.  This range will
               include ``left_current`` pages before, and
               ``right_current`` pages after the current page.  This
               range always includes the current page.

            3. Finally, a range (always ending at the last page) at
               the end of the page sequence.  The length of this range
               is specified by the ``right_edge`` argument.

        If any of these ranges overlap, they will be merged.  A
        ``None`` will be inserted between non-overlapping ranges to
        signify that pages have been elided.

        This is how you could render such a pagination in the templates:
        .. sourcecode:: html+jinja
            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>...</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}

        """
        last = 0
        for num in range(1, self.pages + 1):
            # pylint: disable=chained-comparison
            if (
                num <= left_edge
                or (
                    num >= self.page - left_current and num <= self.page + right_current
                )
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num
        if last != self.pages:
            yield None
