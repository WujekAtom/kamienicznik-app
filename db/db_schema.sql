-- DROP SCHEMA public;


-- DROP TYPE public."billingstatus";

CREATE TYPE public."billingstatus" AS ENUM (
	'draft',
	'issued',
	'paid',
	'overdue');

-- DROP TYPE public."contracttype";

CREATE TYPE public."contracttype" AS ENUM (
	'fixed',
	'indefinite');

-- DROP TYPE public."paymenttype";

CREATE TYPE public."paymenttype" AS ENUM (
	'cash',
	'transfer',
	'mixed');

-- DROP TYPE public."userrole";

CREATE TYPE public."userrole" AS ENUM (
	'admin',
	'tenant');

-- DROP TYPE public."utilitytype";

CREATE TYPE public."utilitytype" AS ENUM (
	'water',
	'electricity',
	'gas',
	'trash',
	'heating',
	'community_fee');

-- DROP SEQUENCE public.apartments_id_seq;

CREATE SEQUENCE public.apartments_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.billing_items_id_seq;

CREATE SEQUENCE public.billing_items_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.billing_periods_id_seq;

CREATE SEQUENCE public.billing_periods_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.electricity_components_id_seq;

CREATE SEQUENCE public.electricity_components_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.gas_components_id_seq;

CREATE SEQUENCE public.gas_components_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.meter_readings_id_seq;

CREATE SEQUENCE public.meter_readings_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.payments_id_seq;

CREATE SEQUENCE public.payments_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.tenants_id_seq;

CREATE SEQUENCE public.tenants_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.users_id_seq;

CREATE SEQUENCE public.users_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.utility_rates_id_seq;

CREATE SEQUENCE public.utility_rates_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;-- public.apartments definition

-- Drop table

-- DROP TABLE public.apartments;

CREATE TABLE public.apartments (
	id serial4 NOT NULL,
	address varchar(500) NOT NULL,
	description text NULL,
	has_water bool NULL,
	has_electricity bool NULL,
	has_gas bool NULL,
	has_trash bool NULL,
	has_heating bool NULL,
	is_active bool NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT apartments_pkey PRIMARY KEY (id)
);
CREATE INDEX ix_apartments_id ON public.apartments USING btree (id);


-- public.billing_periods definition

-- Drop table

-- DROP TABLE public.billing_periods;

CREATE TABLE public.billing_periods (
	id serial4 NOT NULL,
	apartment_id int4 NOT NULL,
	period_start date NOT NULL,
	period_end date NOT NULL,
	rent_amount numeric(10, 2) NOT NULL,
	total_utilities numeric(10, 2) NOT NULL,
	total_amount numeric(10, 2) NOT NULL,
	amount_paid numeric(10, 2) NOT NULL,
	status public."billingstatus" NOT NULL,
	due_date date NOT NULL,
	notes text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT billing_periods_pkey PRIMARY KEY (id),
	CONSTRAINT billing_periods_apartment_id_fkey FOREIGN KEY (apartment_id) REFERENCES public.apartments(id) ON DELETE CASCADE
);
CREATE INDEX ix_billing_periods_id ON public.billing_periods USING btree (id);


-- public.electricity_components definition

-- Drop table

-- DROP TABLE public.electricity_components;

CREATE TABLE public.electricity_components (
	id serial4 NOT NULL,
	valid_from date NOT NULL,
	valid_to date NULL,
	notes text NULL,
	var_rate numeric(10, 6) NOT NULL,
	extra_trade_cycle numeric(10, 4) NOT NULL,
	fixed_price numeric(10, 4) NOT NULL,
	dist_fixed numeric(10, 4) NOT NULL,
	transition_fee numeric(10, 6) NOT NULL,
	abonament numeric(10, 4) NOT NULL,
	power_fee numeric(10, 4) NOT NULL,
	quality_rate numeric(10, 6) NOT NULL,
	dist_variable numeric(10, 6) NOT NULL,
	oze_rate numeric(10, 6) NOT NULL,
	cogen_rate numeric(10, 6) NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	apartment_id int4 NULL,
	CONSTRAINT electricity_components_pkey PRIMARY KEY (id),
	CONSTRAINT electricity_components_apartment_id_fkey FOREIGN KEY (apartment_id) REFERENCES public.apartments(id) ON DELETE CASCADE
);
CREATE INDEX ix_electricity_components_id ON public.electricity_components USING btree (id);


-- public.gas_components definition

-- Drop table

-- DROP TABLE public.gas_components;

CREATE TABLE public.gas_components (
	id serial4 NOT NULL,
	valid_from date NOT NULL,
	valid_to date NULL,
	notes text NULL,
	abonament numeric(10, 4) NOT NULL,
	conv_factor numeric(10, 6) NOT NULL,
	gas_price_per_kwh numeric(10, 6) NOT NULL,
	vat_pct numeric(5, 2) NOT NULL,
	dist_fixed numeric(10, 4) NOT NULL,
	dist_variable numeric(10, 6) NOT NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	apartment_id int4 NULL,
	CONSTRAINT gas_components_pkey PRIMARY KEY (id),
	CONSTRAINT gas_components_apartment_id_fkey FOREIGN KEY (apartment_id) REFERENCES public.apartments(id) ON DELETE CASCADE
);
CREATE INDEX ix_gas_components_id ON public.gas_components USING btree (id);


-- public.tenants definition

-- Drop table

-- DROP TABLE public.tenants;

CREATE TABLE public.tenants (
	id serial4 NOT NULL,
	apartment_id int4 NOT NULL,
	full_name varchar(255) NOT NULL,
	email varchar(255) NULL,
	phone varchar(50) NULL,
	id_number varchar(100) NULL,
	contract_start date NOT NULL,
	contract_end date NULL,
	contract_type public."contracttype" NOT NULL,
	payment_due_day int4 NOT NULL,
	rent_amount numeric(10, 2) NOT NULL,
	is_active bool NOT NULL,
	notes varchar(1000) NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	occupants int4 DEFAULT 1 NOT NULL,
	water_advance numeric(10, 2) DEFAULT 0 NOT NULL,
	CONSTRAINT tenants_pkey PRIMARY KEY (id),
	CONSTRAINT tenants_apartment_id_fkey FOREIGN KEY (apartment_id) REFERENCES public.apartments(id) ON DELETE CASCADE
);
CREATE INDEX ix_tenants_id ON public.tenants USING btree (id);


-- public.users definition

-- Drop table

-- DROP TABLE public.users;

CREATE TABLE public.users (
	id serial4 NOT NULL,
	email varchar(255) NOT NULL,
	hashed_password varchar(255) NULL,
	"role" public."userrole" NOT NULL,
	is_active bool NOT NULL,
	magic_link_token varchar(255) NULL,
	magic_link_expires timestamptz NULL,
	tenant_id int4 NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	reset_token varchar(255) NULL,
	reset_token_expires timestamptz NULL,
	CONSTRAINT users_pkey PRIMARY KEY (id),
	CONSTRAINT users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);
CREATE INDEX ix_users_id ON public.users USING btree (id);
CREATE UNIQUE INDEX ix_users_magic_link_token ON public.users USING btree (magic_link_token);


-- public.utility_rates definition

-- Drop table

-- DROP TABLE public.utility_rates;

CREATE TABLE public.utility_rates (
	id serial4 NOT NULL,
	utility_type public."utilitytype" NOT NULL,
	rate_per_unit numeric(10, 4) NOT NULL,
	unit_label varchar(20) NOT NULL,
	valid_from date NOT NULL,
	valid_to date NULL,
	notes text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	apartment_id int4 NULL,
	CONSTRAINT utility_rates_pkey PRIMARY KEY (id),
	CONSTRAINT utility_rates_apartment_id_fkey FOREIGN KEY (apartment_id) REFERENCES public.apartments(id) ON DELETE CASCADE
);
CREATE INDEX ix_utility_rates_id ON public.utility_rates USING btree (id);


-- public.meter_readings definition

-- Drop table

-- DROP TABLE public.meter_readings;

CREATE TABLE public.meter_readings (
	id serial4 NOT NULL,
	apartment_id int4 NOT NULL,
	utility_type public."utilitytype" NOT NULL,
	reading_date date NOT NULL,
	reading_value numeric(12, 3) NOT NULL,
	consumption numeric(12, 3) NULL,
	previous_reading_id int4 NULL,
	submitted_by_id int4 NULL,
	photo_path varchar(500) NULL,
	photo_verified bool NULL,
	photo_verified_by_id int4 NULL,
	photo_verified_at timestamptz NULL,
	notes text NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT meter_readings_pkey PRIMARY KEY (id),
	CONSTRAINT meter_readings_apartment_id_fkey FOREIGN KEY (apartment_id) REFERENCES public.apartments(id) ON DELETE CASCADE,
	CONSTRAINT meter_readings_photo_verified_by_id_fkey FOREIGN KEY (photo_verified_by_id) REFERENCES public.users(id),
	CONSTRAINT meter_readings_previous_reading_id_fkey FOREIGN KEY (previous_reading_id) REFERENCES public.meter_readings(id),
	CONSTRAINT meter_readings_submitted_by_id_fkey FOREIGN KEY (submitted_by_id) REFERENCES public.users(id)
);
CREATE INDEX ix_meter_readings_id ON public.meter_readings USING btree (id);


-- public.payments definition

-- Drop table

-- DROP TABLE public.payments;

CREATE TABLE public.payments (
	id serial4 NOT NULL,
	billing_period_id int4 NOT NULL,
	payment_date date NOT NULL,
	amount numeric(10, 2) NOT NULL,
	payment_type public."paymenttype" NOT NULL,
	cash_amount numeric(10, 2) NULL,
	transfer_amount numeric(10, 2) NULL,
	reference_number varchar(255) NULL,
	notes text NULL,
	registered_by_id int4 NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT payments_pkey PRIMARY KEY (id),
	CONSTRAINT payments_billing_period_id_fkey FOREIGN KEY (billing_period_id) REFERENCES public.billing_periods(id) ON DELETE CASCADE,
	CONSTRAINT payments_registered_by_id_fkey FOREIGN KEY (registered_by_id) REFERENCES public.users(id)
);
CREATE INDEX ix_payments_id ON public.payments USING btree (id);


-- public.billing_items definition

-- Drop table

-- DROP TABLE public.billing_items;

CREATE TABLE public.billing_items (
	id serial4 NOT NULL,
	billing_period_id int4 NOT NULL,
	item_type varchar(50) NOT NULL,
	description varchar(500) NOT NULL,
	quantity numeric(12, 3) NULL,
	unit_price numeric(10, 4) NULL,
	total_price numeric(10, 2) NOT NULL,
	reading_from_id int4 NULL,
	reading_to_id int4 NULL,
	created_at timestamptz DEFAULT now() NOT NULL,
	updated_at timestamptz DEFAULT now() NOT NULL,
	CONSTRAINT billing_items_pkey PRIMARY KEY (id),
	CONSTRAINT billing_items_billing_period_id_fkey FOREIGN KEY (billing_period_id) REFERENCES public.billing_periods(id) ON DELETE CASCADE,
	CONSTRAINT billing_items_reading_from_id_fkey FOREIGN KEY (reading_from_id) REFERENCES public.meter_readings(id),
	CONSTRAINT billing_items_reading_to_id_fkey FOREIGN KEY (reading_to_id) REFERENCES public.meter_readings(id)
);
CREATE INDEX ix_billing_items_id ON public.billing_items USING btree (id);
