-- When the current attempt started. An event left in 'processing' (the app was restarted
-- or killed mid-email) can be claimed again once this is old enough.
alter table events add column claimed_at timestamptz not null default now();
