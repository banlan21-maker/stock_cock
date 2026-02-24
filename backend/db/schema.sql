-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Create profiles table (linked to auth.users)
create table public.profiles (
  id uuid references auth.users on delete cascade not null primary key,
  email text,
  username text,
  full_name text,
  avatar_url text,
  coins integer default 0,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table public.profiles enable row level security;

-- Create policies for profiles
create policy "Public profiles are viewable by everyone."
  on profiles for select
  using ( true );

create policy "Users can insert their own profile."
  on profiles for insert
  with check ( auth.uid() = id );

create policy "Users can update own profile."
  on profiles for update
  using ( auth.uid() = id );

-- Create unlocked_stocks table (to track purchased content)
create table public.unlocked_stocks (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  stock_code text not null,
  unlocked_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(user_id, stock_code)
);

-- Enable RLS for unlocked_stocks
alter table public.unlocked_stocks enable row level security;

create policy "Users can view own unlocked stocks."
  on unlocked_stocks for select
  using ( auth.uid() = user_id );

create policy "Users can insert own unlocked stocks."
  on unlocked_stocks for insert
  with check ( auth.uid() = user_id );

-- Function to handle new user signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (new.id, new.email, new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'avatar_url');
  return new;
end;
$$ language plpgsql security definer;

-- Trigger for new user signup
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
