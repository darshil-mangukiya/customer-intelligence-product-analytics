select generated_day::date as date_day
from generate_series(
    date '2020-01-01',
    date '2030-12-31',
    interval '1 day'
) as generated_day
