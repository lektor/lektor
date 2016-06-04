from math import ceil

from lektor._compat import range_type


class Pagination(object):

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
        """The total number of pages"""
        if self.per_page == 0:
            pages = 0
        else:
            pages = int(ceil(self.total / float(self.per_page)))
        return pages

    @property
    def prev_num(self):
        """Number of the previous page."""
        if self.page > 1:
            return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    @property
    def prev(self):
        if not self.has_prev:
            return None
        return self.config.get_record_for_page(self.current,
                                               self.page - 1)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        if self.page < self.pages:
            return self.page + 1

    @property
    def next(self):
        if not self.has_next:
            return None
        return self.config.get_record_for_page(self.current,
                                               self.page + 1)

    def for_page(self, page):
        """Returns the pagination for a specific page."""
        if 1 <= page <= self.pages:
            return self.config.get_record_for_page(self.current, page)

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
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
        for num in range_type(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num
