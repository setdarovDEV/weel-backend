#!/usr/bin/env python3
"""
Weel Database Migration Script
Migrate data from old Django production DB to new FastAPI 5NF DB
"""
import os
import sys
import uuid
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional
from decimal import Decimal

# Add backend to path
sys.path.insert(0, '/home/abbbose/weel/weel-backend')

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Connection strings
OLD_DB_URL = "postgresql://postgres:2lfFO74FFWQvS2NChyeK@46.62.220.230:5433/production"
NEW_DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5433/weel"

# Direct psycopg2 connections
old_conn = psycopg2.connect(OLD_DB_URL)
new_conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5433/weel")

old_cur = old_conn.cursor(cursor_factory=RealDictCursor)
new_cur = new_conn.cursor()

def reset_new_db():
    """Truncate all tables in new DB and reset sequences"""
    print("Resetting new database...")
    new_cur.execute("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%' AND tablename NOT LIKE 'sql_%')
            LOOP
                EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
    """)
    new_conn.commit()
    print("New database reset complete.")

def migrate_regions():
    print("Migrating regions...")
    old_cur.execute("SELECT id, guid, title_uz, title_ru, title_en, img FROM region ORDER BY id")
    rows = old_cur.fetchall()
    
    id_map = {}
    for row in rows:
        new_cur.execute("""
            INSERT INTO regions (id, guid, title_uz, title_ru, img_url)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET guid = EXCLUDED.guid
            RETURNING id
        """, (row['id'], str(row['guid']), row['title_uz'], row['title_ru'], row.get('img')))
        result = new_cur.fetchone()
        id_map[row['id']] = result[0] if result else row['id']
    
    new_conn.commit()
    print(f"  Migrated {len(rows)} regions")
    return id_map

def migrate_districts(region_map):
    print("Migrating districts...")
    old_cur.execute("SELECT id, guid, title_uz, title_ru, region_id FROM district ORDER BY id")
    rows = old_cur.fetchall()
    
    id_map = {}
    for row in rows:
        new_region_id = region_map.get(row['region_id'], row['region_id'])
        new_cur.execute("""
            INSERT INTO districts (id, guid, region_id, title_uz, title_ru)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET guid = EXCLUDED.guid
            RETURNING id
        """, (row['id'], str(row['guid']), new_region_id, row['title_uz'], row['title_ru']))
        result = new_cur.fetchone()
        id_map[row['id']] = result[0] if result else row['id']
    
    new_conn.commit()
    print(f"  Migrated {len(rows)} districts")
    return id_map

def migrate_property_types():
    print("Migrating property types...")
    # Create default property types
    now = datetime.now(timezone.utc)
    types = [
        (str(uuid.uuid4()), 'Dacha / Cottage', 'Dacha / Cottage', None, 'cottage', now),
        (str(uuid.uuid4()), 'Kvartira / Apartment', 'Kvartira / Apartment', None, 'apartment', now),
    ]
    type_map = {}
    for t in types:
        new_cur.execute("""
            INSERT INTO property_types (guid, title_ru, title_uz, icon_url, slug, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET title_ru = EXCLUDED.title_ru
            RETURNING guid
        """, t)
        result = new_cur.fetchone()
        if result and result[0]:
            type_map[t[4]] = result[0]
        else:
            # If RETURNING didn't work, fetch existing
            new_cur.execute("SELECT guid FROM property_types WHERE slug = %s", (t[4],))
            existing = new_cur.fetchone()
            type_map[t[4]] = existing[0] if existing else t[0]
    
    new_conn.commit()
    print(f"  Migrated {len(types)} property types")
    return type_map

def migrate_services(property_type_map):
    print("Migrating services...")
    old_cur.execute("SELECT id, icon_url, title, title_ru, type FROM services")
    rows = old_cur.fetchall()
    
    id_map = {}
    for row in rows:
        service_uuid = str(uuid.uuid4())
        # Map to cottage type by default (or apartment if type indicates)
        pt_id = property_type_map.get('cottage')
        if row.get('type') and isinstance(row['type'], list):
            if 'apartment' in [t.lower() for t in row['type']]:
                pt_id = property_type_map.get('apartment')
        new_cur.execute("""
            INSERT INTO property_services (guid, title_ru, title_uz, icon_url, property_type_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING guid
        """, (service_uuid, row.get('title_ru') or row['title'], row['title'], row.get('icon_url') or 'property/icons/default.svg', pt_id))
        result = new_cur.fetchone()
        sid = result[0] if result else service_uuid
        id_map[str(row['id'])] = sid
    
    new_conn.commit()
    print(f"  Migrated {len(rows)} services")
    return id_map

def ensure_partner_records(user_map, partner_ids):
    """Ensure all users referenced as property partners have partner records"""
    old_cur.execute("""
        SELECT id, first_name, last_name, username, avatar, created_at, updated_at
        FROM users WHERE id = ANY(%s)
    """, (partner_ids,))
    rows = old_cur.fetchall()
    
    partner_data = []
    for row in rows:
        user_uuid = user_map.get(row['id'])
        if not user_uuid:
            continue
        # Check if already has partner record
        new_cur.execute("SELECT 1 FROM partners WHERE user_id = %s", (user_uuid,))
        if new_cur.fetchone():
            continue
        partner_data.append((
            user_uuid, row.get('username'), row.get('first_name'), row.get('last_name'),
            row.get('avatar'), 'verified', row['created_at'], row['updated_at']
        ))
    
    if partner_data:
        execute_values(new_cur, """
            INSERT INTO partners (user_id, username, first_name, last_name, avatar_url, verification_status, created_at, updated_at)
            VALUES %s ON CONFLICT DO NOTHING
        """, partner_data)
        new_conn.commit()
    
    print(f"  Created {len(partner_data)} additional partner records")


def migrate_users():
    print("Migrating users...")
    old_cur.execute("""
        SELECT id, role, email, phone_number, first_name, last_name, username, 
               avatar, is_active, is_verified, verified_at, created_at, updated_at,
               fcm_token, device_type
        FROM users ORDER BY id
    """)
    rows = old_cur.fetchall()
    
    user_map = {}  # old_id -> new_uuid
    client_data = []
    partner_data = []
    admin_data = []
    role_data = []
    device_data = []
    seen_phones = set()
    
    for row in rows:
        phone = row.get('phone_number') or f"unknown_{row['id']}"
        
        # Skip duplicate phone numbers (keep first occurrence)
        if phone in seen_phones:
            print(f"    Skipping duplicate phone: {phone} (user_id={row['id']})")
            continue
        seen_phones.add(phone)
        
        new_uuid = str(uuid.uuid4())
        user_map[row['id']] = new_uuid
        
        new_cur.execute("""
            INSERT INTO users (guid, phone_number, created_at, updated_at, is_active, is_deleted)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (new_uuid, phone, row['created_at'], row['updated_at'], 
                row.get('is_active', True), False))
        
        # Roles
        role = row.get('role', 'client')
        if role:
            role_data.append((new_uuid, role, row['created_at']))
        
        # Client profile
        if role == 'client':
            client_data.append((new_uuid, row.get('first_name'), row.get('last_name'), row['created_at'], row['updated_at']))
        
        # Partner profile
        elif role == 'partner':
            partner_data.append((
                new_uuid, row.get('username'), row.get('first_name'), row.get('last_name'),
                row.get('avatar'), 'waiting', row['created_at'], row['updated_at']
            ))
        
        # Admin profile
        elif role == 'admin':
            # Hash password for admin (use default)
            pw_hash = hashlib.sha256(b"admin123").hexdigest()
            admin_data.append((new_uuid, row.get('email') or f"admin_{row['id']}@weel.uz", pw_hash, True, False, row['created_at']))
        
        # Device
        if row.get('fcm_token'):
            device_data.append((new_uuid, row['fcm_token'], row.get('device_type') or 'android', row['created_at']))
    
    # Batch insert roles
    if role_data:
        execute_values(new_cur, """
            INSERT INTO user_roles (user_id, role, created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, role_data)
    
    # Batch insert clients
    if client_data:
        execute_values(new_cur, """
            INSERT INTO clients (user_id, first_name, last_name, created_at, updated_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, client_data)
    
    # Batch insert partners
    if partner_data:
        execute_values(new_cur, """
            INSERT INTO partners (user_id, username, first_name, last_name, avatar_url, verification_status, created_at, updated_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, partner_data)
    
    # Batch insert admins
    if admin_data:
        execute_values(new_cur, """
            INSERT INTO admins (user_id, email, password_hash, is_staff, is_superuser, created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, admin_data)
    
    # Batch insert devices
    if device_data:
        execute_values(new_cur, """
            INSERT INTO user_devices (user_id, fcm_token, device_type, created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, device_data)
    
    new_conn.commit()
    print(f"  Migrated {len(rows)} users ({len(client_data)} clients, {len(partner_data)} partners, {len(admin_data)} admins)")
    return user_map

def migrate_properties(user_map, property_type_map, region_map, district_map, service_map):
    print("Migrating cottages...")
    old_cur.execute("""
        SELECT id, legacy_property_id, guid, created_at, updated_at, title, title_sort,
               is_verified, verified_at, verification_status, is_archived, is_recommended,
               price_per_person, price_on_working_days, price_on_weekends, currency,
               img, partner_user_id, latitude, longitude, city, country,
               description_en, description_ru, description_uz, check_in, check_out,
               is_allowed_alcohol, is_allowed_corporate, is_allowed_pets, is_quiet_hours,
               services, prefecture_id, region_id, district_id, guests, rooms, beds, bathrooms
        FROM cottage ORDER BY id
    """)
    cottage_rows = old_cur.fetchall()
    
    property_map = {}  # old_property_id -> new_property_uuid
    image_data = []
    service_link_data = []
    price_data = []
    
    cottage_type_id = property_type_map.get('cottage')
    
    for row in cottage_rows:
        prop_uuid = str(row['guid']) if row.get('guid') else str(uuid.uuid4())
        partner_uuid = user_map.get(row['partner_user_id'])
        if not partner_uuid:
            continue
        
        vs = row.get('verification_status') or 'waiting'
        if vs == 'accepted':
            vs = 'verified'
        
        new_cur.execute("""
            INSERT INTO properties (guid, partner_id, property_type_id, title, currency,
                verification_status, is_archived, is_recommended, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (guid) DO NOTHING
        """, (prop_uuid, partner_uuid, cottage_type_id, row['title'],
                row.get('currency') or 'UZS', vs, row.get('is_archived', False),
                row.get('is_recommended', False), row['created_at'], row['updated_at']))
        
        property_map[row['id']] = prop_uuid
        
        # Location
        region_id = region_map.get(row.get('region_id')) if row.get('region_id') else None
        district_id = district_map.get(row.get('district_id')) if row.get('district_id') else None
        new_cur.execute("""
            INSERT INTO property_locations (property_id, latitude, longitude, country, city, region_id, district_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid, str(row['latitude']) if row.get('latitude') else None,
                str(row['longitude']) if row.get('longitude') else None,
                row.get('country') or 'Uzbekistan', row.get('city') or 'Unknown',
                region_id, district_id))
        
        # Details
        new_cur.execute("""
            INSERT INTO property_details (property_id, description_ru, description_uz, description_en,
                check_in_time, check_out_time, is_allowed_alcohol, is_allowed_pets, is_allowed_corporate, is_quiet_hours)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid, row.get('description_ru'), row.get('description_uz'), row.get('description_en'),
                str(row['check_in'])[:5] if row.get('check_in') else None,
                str(row['check_out'])[:5] if row.get('check_out') else None,
                row.get('is_allowed_alcohol', False), row.get('is_allowed_pets', False),
                row.get('is_allowed_corporate', False), row.get('is_quiet_hours', False)))
        
        # Rooms
        new_cur.execute("""
            INSERT INTO property_rooms (property_id, guests, bedrooms, beds, bathrooms)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid, row.get('guests') or 1, row.get('rooms') or 0,
                row.get('beds') or 1, row.get('bathrooms') or 1))
        
        # Cottage specific
        new_cur.execute("""
            INSERT INTO cottages (property_id)
            VALUES (%s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid,))
        
        # Images
        if row.get('img'):
            for idx, img_url in enumerate(row['img']):
                if img_url:
                    img_uuid = str(uuid.uuid4())
                    image_data.append((img_uuid, prop_uuid, img_url, idx, row['created_at']))
        
        # Services
        if row.get('services'):
            for sid in row['services']:
                nsid = service_map.get(str(sid))
                if nsid:
                    service_link_data.append((prop_uuid, nsid, row['created_at']))
        
        # Prices
        if row.get('price_on_working_days') or row.get('price_on_weekends') or row.get('price_per_person'):
            price_data.append((
                prop_uuid, 1, 12,
                int(row['price_per_person'] or 0),
                int(row['price_on_working_days'] or 0),
                int(row['price_on_weekends'] or 0),
                row['created_at']
            ))
    
    # Batch insert images
    if image_data:
        execute_values(new_cur, """
            INSERT INTO property_images (guid, property_id, image_url, "order", created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, image_data)
    
    # Batch insert service links
    if service_link_data:
        execute_values(new_cur, """
            INSERT INTO property_service_links (property_id, service_id, created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, service_link_data)
    
    # Batch insert prices
    if price_data:
        execute_values(new_cur, """
            INSERT INTO property_prices (property_id, month_from, month_to, price_per_person, price_on_working_days, price_on_weekends, created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, price_data)
    
    new_conn.commit()
    print(f"  Migrated {len(cottage_rows)} cottages")
    
    # Now migrate apartments
    print("Migrating apartments...")
    old_cur.execute("""
        SELECT id, legacy_property_id, guid, created_at, updated_at, title, title_sort,
               is_verified, verified_at, verification_status, is_archived, is_recommended,
               price, currency, img, partner_user_id, latitude, longitude, city, country,
               description_en, description_ru, description_uz, check_in, check_out,
               is_allowed_alcohol, is_allowed_corporate, is_allowed_pets, is_quiet_hours,
               services, prefecture_id, region_id, district_id, guests, rooms, beds, bathrooms,
               apartment_number, home_number, entrance_number, floor_number, pass_code
        FROM apartment ORDER BY id
    """)
    apt_rows = old_cur.fetchall()
    
    apartment_type_id = property_type_map.get('apartment')
    image_data = []
    service_link_data = []
    
    for row in apt_rows:
        prop_uuid = str(row['guid']) if row.get('guid') else str(uuid.uuid4())
        partner_uuid = user_map.get(row['partner_user_id'])
        if not partner_uuid:
            continue
        
        vs = row.get('verification_status') or 'waiting'
        if vs == 'accepted':
            vs = 'verified'
        
        new_cur.execute("""
            INSERT INTO properties (guid, partner_id, property_type_id, title, currency,
                verification_status, is_archived, is_recommended, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (guid) DO NOTHING
        """, (prop_uuid, partner_uuid, apartment_type_id, row['title'],
                row.get('currency') or 'UZS', vs, row.get('is_archived', False),
                row.get('is_recommended', False), row['created_at'], row['updated_at']))
        
        property_map[row['id']] = prop_uuid
        
        # Location
        region_id = region_map.get(row.get('region_id')) if row.get('region_id') else None
        district_id = district_map.get(row.get('district_id')) if row.get('district_id') else None
        new_cur.execute("""
            INSERT INTO property_locations (property_id, latitude, longitude, country, city, region_id, district_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid, str(row['latitude']) if row.get('latitude') else None,
                str(row['longitude']) if row.get('longitude') else None,
                row.get('country') or 'Uzbekistan', row.get('city') or 'Unknown',
                region_id, district_id))
        
        # Details
        new_cur.execute("""
            INSERT INTO property_details (property_id, description_ru, description_uz, description_en,
                check_in_time, check_out_time, is_allowed_alcohol, is_allowed_pets, is_allowed_corporate, is_quiet_hours)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid, row.get('description_ru'), row.get('description_uz'), row.get('description_en'),
                str(row['check_in'])[:5] if row.get('check_in') else None,
                str(row['check_out'])[:5] if row.get('check_out') else None,
                row.get('is_allowed_alcohol', False), row.get('is_allowed_pets', False),
                row.get('is_allowed_corporate', False), row.get('is_quiet_hours', False)))
        
        # Rooms
        new_cur.execute("""
            INSERT INTO property_rooms (property_id, guests, bedrooms, beds, bathrooms)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid, row.get('guests') or 1, row.get('rooms') or 0,
                row.get('beds') or 1, row.get('bathrooms') or 1))
        
        # Apartment specific
        new_cur.execute("""
            INSERT INTO apartments (property_id, apartment_number, home_number, entrance_number, floor_number, pass_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (prop_uuid, row.get('apartment_number'), row.get('home_number'),
                row.get('entrance_number'), row.get('floor_number'), row.get('pass_code')))
        
        # Images
        if row.get('img'):
            for idx, img_url in enumerate(row['img']):
                if img_url:
                    img_uuid = str(uuid.uuid4())
                    image_data.append((img_uuid, prop_uuid, img_url, idx, row['created_at']))
        
        # Services
        if row.get('services'):
            for sid in row['services']:
                nsid = service_map.get(str(sid))
                if nsid:
                    service_link_data.append((prop_uuid, nsid, row['created_at']))
    
    # Batch insert remaining
    if image_data:
        execute_values(new_cur, """
            INSERT INTO property_images (guid, property_id, image_url, "order", created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, image_data)
    
    if service_link_data:
        execute_values(new_cur, """
            INSERT INTO property_service_links (property_id, service_id, created_at) VALUES %s
            ON CONFLICT DO NOTHING
        """, service_link_data)
    
    new_conn.commit()
    print(f"  Migrated {len(apt_rows)} apartments")
    print(f"  Total properties: {len(property_map)}")
    return property_map

def migrate_bookings(user_map, property_map):
    print("Migrating bookings...")
    old_cur.execute("""
        SELECT id, legacy_booking_id, guid, created_at, updated_at, booking_number,
               check_in, check_out, adults, children, babies, reminder_sent, status,
               cancellation_reason, confirmed_at, cancelled_at, completed_at,
               payment_reminder_stage, client_user_id, property_apartment_id, property_cottage_id
        FROM booking ORDER BY id
    """)
    rows = old_cur.fetchall()
    
    booking_data = []
    for row in rows:
        client_uuid = user_map.get(row['client_user_id'])
        prop_uuid = None
        if row.get('property_cottage_id'):
            prop_uuid = property_map.get(row['property_cottage_id'])
        elif row.get('property_apartment_id'):
            prop_uuid = property_map.get(row['property_apartment_id'])
        
        if not client_uuid or not prop_uuid:
            continue
        
        booking_uuid = str(row['guid']) if row.get('guid') else str(uuid.uuid4())
        booking_data.append((
            booking_uuid, client_uuid, prop_uuid, row['booking_number'],
            row['check_in'], row['check_out'], row.get('adults', 1), row.get('children', 0), row.get('babies', 0),
            row.get('status', 'pending'), row.get('cancellation_reason'),
            row['created_at'], row['updated_at']
        ))
    
    if booking_data:
        execute_values(new_cur, """
            INSERT INTO bookings (guid, client_id, property_id, booking_number, check_in, check_out,
                adults, children, babies, status, cancellation_reason, created_at, updated_at)
            VALUES %s ON CONFLICT (guid) DO NOTHING
        """, booking_data)
    
    new_conn.commit()
    print(f"  Migrated {len(booking_data)} bookings")

def ensure_client_records_for_reviews(user_map):
    """Ensure all users who wrote reviews have client records"""
    old_cur.execute("SELECT DISTINCT user_id FROM review WHERE user_id IS NOT NULL")
    reviewer_ids = [r['user_id'] for r in old_cur.fetchall()]
    
    client_data = []
    for old_id in reviewer_ids:
        user_uuid = user_map.get(old_id)
        if not user_uuid:
            continue
        # Check if already has client record
        new_cur.execute("SELECT 1 FROM clients WHERE user_id = %s", (user_uuid,))
        if new_cur.fetchone():
            continue
        # Get user info from old DB
        old_cur.execute("SELECT first_name, last_name, created_at, updated_at FROM users WHERE id = %s", (old_id,))
        u = old_cur.fetchone()
        if u:
            client_data.append((user_uuid, u['first_name'], u['last_name'], u['created_at'], u['updated_at']))
    
    if client_data:
        execute_values(new_cur, """
            INSERT INTO clients (user_id, first_name, last_name, created_at, updated_at)
            VALUES %s ON CONFLICT DO NOTHING
        """, client_data)
        new_conn.commit()
    
    print(f"  Created {len(client_data)} client records for reviewers")


def migrate_reviews(user_map, property_map):
    print("Migrating reviews...")
    old_cur.execute("""
        SELECT id, guid, created_at, updated_at, rating, comment, is_hidden, user_id, apartment_id, cottage_id
        FROM review ORDER BY id
    """)
    rows = old_cur.fetchall()
    
    review_data = []
    for row in rows:
        client_uuid = user_map.get(row['user_id'])
        prop_uuid = None
        if row.get('cottage_id'):
            prop_uuid = property_map.get(row['cottage_id'])
        elif row.get('apartment_id'):
            prop_uuid = property_map.get(row['apartment_id'])
        
        if not client_uuid or not prop_uuid:
            continue
        
        review_uuid = str(row['guid']) if row.get('guid') else str(uuid.uuid4())
        review_data.append((
            review_uuid, client_uuid, prop_uuid, float(row.get('rating') or 5),
            row.get('comment'), row['created_at'], row['updated_at']
        ))
    
    if review_data:
        execute_values(new_cur, """
            INSERT INTO reviews (guid, client_id, property_id, rating, comment, created_at, updated_at)
            VALUES %s ON CONFLICT (guid) DO NOTHING
        """, review_data)
    
    new_conn.commit()
    print(f"  Migrated {len(review_data)} reviews")

def migrate_chat(user_map):
    print("Migrating chat conversations and messages...")
    old_cur.execute("""
        SELECT id, legacy_conversation_id, created_at, updated_at, admin_user_id, partner_user_id, client_user_id
        FROM chat_conversation ORDER BY id
    """)
    conv_rows = old_cur.fetchall()
    
    conv_map = {}
    conv_data = []
    for row in conv_rows:
        conv_uuid = str(uuid.uuid4())
        admin_uuid = user_map.get(row['admin_user_id'])
        partner_uuid = user_map.get(row['partner_user_id'])
        client_uuid = user_map.get(row['client_user_id'])
        
        if not admin_uuid or not partner_uuid:
            continue
        
        # Use generic participant model: admin + partner (or client if available)
        p1_id = admin_uuid
        p1_type = 'admin'
        p2_id = client_uuid if client_uuid else partner_uuid
        p2_type = 'client' if client_uuid else 'partner'
        
        conv_data.append((conv_uuid, p1_id, p1_type, p2_id, p2_type, row['created_at']))
        conv_map[row['id']] = conv_uuid
    
    if conv_data:
        execute_values(new_cur, """
            INSERT INTO conversations (guid, participant_1_id, participant_1_type, participant_2_id, participant_2_type, created_at)
            VALUES %s ON CONFLICT DO NOTHING
        """, conv_data)
    
    new_conn.commit()
    print(f"  Migrated {len(conv_data)} conversations")
    
    # Messages
    old_cur.execute("""
        SELECT id, content, is_read, created_at, updated_at, conversation_id, sender_user_id, receiver_user_id, sender_role, receiver_role
        FROM chat_message ORDER BY id
    """)
    msg_rows = old_cur.fetchall()
    
    msg_data = []
    for row in msg_rows:
        conv_uuid = conv_map.get(row['conversation_id'])
        sender_uuid = user_map.get(row['sender_user_id'])
        receiver_uuid = user_map.get(row['receiver_user_id'])
        
        if not conv_uuid or not sender_uuid or not receiver_uuid:
            continue
        
        msg_uuid = str(uuid.uuid4())
        sender_type = row.get('sender_role', 'client')
        receiver_type = row.get('receiver_role', 'partner')
        msg_data.append((
            msg_uuid, conv_uuid, sender_uuid, sender_type, receiver_uuid, receiver_type,
            row['content'], row.get('is_read', False), row['created_at']
        ))
    
    if msg_data:
        execute_values(new_cur, """
            INSERT INTO messages (guid, conversation_id, sender_id, sender_type, receiver_id, receiver_type, content, is_read, created_at)
            VALUES %s ON CONFLICT DO NOTHING
        """, msg_data)
    
    new_conn.commit()
    print(f"  Migrated {len(msg_data)} messages")

def migrate_notifications(user_map):
    print("Migrating notifications...")
    old_cur.execute("""
        SELECT id, guid, created_at, updated_at, title, push_message, notification_type,
               status, is_for_every_one, recipient_user_id, recipient_role, payload
        FROM notification ORDER BY id
    """)
    rows = old_cur.fetchall()
    
    notif_data = []
    for row in rows:
        recipient_uuid = user_map.get(row['recipient_user_id']) if row.get('recipient_user_id') else None
        if not recipient_uuid:
            continue
        notif_uuid = str(row['guid']) if row.get('guid') else str(uuid.uuid4())
        payload_str = json.dumps(row['payload']) if row.get('payload') else None
        title = row.get('title') or 'Notification'
        body = row.get('push_message') or ''
        
        notif_data.append((
            notif_uuid, recipient_uuid, title, title, body, body,
            row.get('notification_type', 'system'), payload_str,
            row.get('status') == 'read', row['created_at']
        ))
    
    if notif_data:
        execute_values(new_cur, """
            INSERT INTO notifications (guid, user_id, title_ru, title_uz, body_ru, body_uz,
                notification_type, data, is_read, created_at)
            VALUES %s ON CONFLICT DO NOTHING
        """, notif_data)
    
    new_conn.commit()
    print(f"  Migrated {len(notif_data)} notifications")

def migrate_calendar(property_map):
    print("Migrating calendar...")
    old_cur.execute("""
        SELECT id, guid, created_at, updated_at, status, date, property_apartment_id, property_cottage_id
        FROM calendar ORDER BY id
    """)
    rows = old_cur.fetchall()
    
    cal_data = []
    for row in rows:
        prop_uuid = None
        if row.get('property_cottage_id'):
            prop_uuid = property_map.get(row['property_cottage_id'])
        elif row.get('property_apartment_id'):
            prop_uuid = property_map.get(row['property_apartment_id'])
        
        if not prop_uuid:
            continue
        
        cal_data.append((
            prop_uuid, row['date'], row.get('status', 'available'), row['created_at']
        ))
    
    if cal_data:
        execute_values(new_cur, """
            INSERT INTO calendar_dates (property_id, date, status, created_at)
            VALUES %s ON CONFLICT DO NOTHING
        """, cal_data)
    
    new_conn.commit()
    print(f"  Migrated {len(cal_data)} calendar entries")

def migrate_stories(user_map, property_map):
    print("Migrating stories...")
    old_cur.execute("""
        SELECT id, legacy_story_id, guid, created_at, updated_at, is_verified, verified_at,
               expires_at, views, uploaded_at, verified_by_user_id, property_apartment_id, property_cottage_id
        FROM stories ORDER BY id
    """)
    rows = old_cur.fetchall()
    
    story_map = {}
    story_data = []
    for row in rows:
        partner_uuid = None
        prop_uuid = None
        if row.get('property_cottage_id'):
            prop_uuid = property_map.get(row['property_cottage_id'])
        elif row.get('property_apartment_id'):
            prop_uuid = property_map.get(row['property_apartment_id'])
        
        if not prop_uuid:
            continue
        
        # Find partner from property
        new_cur.execute("SELECT partner_id FROM properties WHERE guid = %s", (prop_uuid,))
        result = new_cur.fetchone()
        if result:
            partner_uuid = result[0]
        
        story_uuid = str(row['guid']) if row.get('guid') else str(uuid.uuid4())
        expires_at = row.get('expires_at') or row['created_at']
        story_data.append((
            story_uuid, prop_uuid, partner_uuid, row['created_at'], expires_at, row.get('is_verified', False)
        ))
        story_map[row['id']] = story_uuid
    
    if story_data:
        execute_values(new_cur, """
            INSERT INTO stories (guid, property_id, partner_id, created_at, expires_at, is_verified)
            VALUES %s ON CONFLICT DO NOTHING
        """, story_data)
    
    new_conn.commit()
    print(f"  Migrated {len(story_data)} stories")
    
    # Story media
    old_cur.execute("""
        SELECT id, guid, created_at, updated_at, media, media_type, story_id
        FROM story_media ORDER BY id
    """)
    media_rows = old_cur.fetchall()
    
    media_data = []
    for idx, row in enumerate(media_rows):
        story_uuid = story_map.get(row['story_id'])
        if not story_uuid:
            continue
        
        media_uuid = str(row['guid']) if row.get('guid') else str(uuid.uuid4())
        media_data.append((media_uuid, story_uuid, row['media'], row.get('media_type', 'image'), idx, row['created_at']))
    
    if media_data:
        execute_values(new_cur, """
            INSERT INTO story_media (guid, story_id, media_url, media_type, "order", created_at)
            VALUES %s ON CONFLICT DO NOTHING
        """, media_data)
    
    new_conn.commit()
    print(f"  Migrated {len(media_data)} story media")

def run_migration():
    print("=" * 60)
    print("WEEL DATABASE MIGRATION")
    print("Old: production@46.62.220.230:5433")
    print("New: weel@localhost:5433")
    print("=" * 60)
    
    try:
        reset_new_db()
        
        # Step 1: Migrate location hierarchy
        region_map = migrate_regions()
        district_map = migrate_districts(region_map)
        
        # Step 2: Migrate property types and services
        property_type_map = migrate_property_types()
        service_map = migrate_services(property_type_map)
        
        # Step 3: Migrate users (clients, partners, admins)
        user_map = migrate_users()
        
        # Step 3b: Ensure all users referenced as property partners have partner records
        print("Ensuring partner records for property owners...")
        old_cur.execute("SELECT DISTINCT partner_user_id FROM cottage WHERE partner_user_id IS NOT NULL UNION SELECT DISTINCT partner_user_id FROM apartment WHERE partner_user_id IS NOT NULL")
        partner_ids = [r['partner_user_id'] for r in old_cur.fetchall()]
        ensure_partner_records(user_map, partner_ids)
        
        # Step 4: Migrate properties (cottages and apartments)
        property_map = migrate_properties(user_map, property_type_map, region_map, district_map, service_map)
        
        # Step 5: Migrate bookings
        migrate_bookings(user_map, property_map)
        
        # Step 5b: Ensure all review authors have client records
        ensure_client_records_for_reviews(user_map)
        
        # Step 6: Migrate reviews
        migrate_reviews(user_map, property_map)
        
        # Step 7: Migrate chat
        migrate_chat(user_map)
        
        # Step 8: Migrate notifications
        migrate_notifications(user_map)
        
        # Step 9: Migrate calendar
        migrate_calendar(property_map)
        
        # Step 10: Migrate stories
        migrate_stories(user_map, property_map)
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nMIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        new_conn.rollback()
    finally:
        old_cur.close()
        new_cur.close()
        old_conn.close()
        new_conn.close()

if __name__ == "__main__":
    run_migration()
