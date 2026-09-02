import os
import sys
import click
import random
import uuid
import psycopg
from datetime import datetime, timezone, timedelta
from faker import Faker
import socket
import struct

PRESETS = {
    "dev": (1000, 100, 10000, 20, 10, 50000),
    "medium": (100000, 5000, 500000, 200, 100, 1000000),
    "large": (1000000, 20000, 5000000, 500, 250, 10000000),
    "stress": (5000000, 50000, 20000000, 2000, 1000, 50000000)
}

def generate_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))

def get_random_rfc1918_ip(rand):
    class_choice = rand.randint(1, 3)
    if class_choice == 1:
        return f"10.{rand.randint(0, 255)}.{rand.randint(0, 255)}.{rand.randint(0, 255)}"
    elif class_choice == 2:
        return f"172.{rand.randint(16, 31)}.{rand.randint(0, 255)}.{rand.randint(0, 255)}"
    else:
        return f"192.168.{rand.randint(0, 255)}.{rand.randint(0, 255)}"

@click.command()
@click.option('--preset', type=click.Choice(['dev', 'medium', 'large', 'stress']), default='dev')
@click.option('--seed', type=int, default=42)
@click.option('--truncate', is_flag=True, help='Truncate tables before generating')
def generate(preset, seed, truncate):
    db_url = os.environ.get("SYNC_DATABASE_URL", "postgresql+psycopg://fwident:change_me_in_production@localhost:5432/fwident")
    db_url_psycopg = db_url.replace("postgresql+psycopg://", "postgresql://")
    
    n_users, n_groups, n_memberships, n_firewalls, n_ldap, n_auth_events = PRESETS[preset]
    
    fake = Faker()
    fake.seed_instance(seed)
    rand = random.Random(seed)
    
    conn = psycopg.connect(db_url_psycopg)
    
    if truncate:
        print("Truncating all tables...")
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE users, groups, firewalls, ldap_servers, 
                         user_group_memberships, user_ip_mappings, 
                         firewall_group_mappings, authentication_events, 
                         diagnostic_runs, audit_logs CASCADE;
            """)
            conn.commit()

    print(f"Generating for {preset} preset...")
    
    # GROUPS
    groups = []
    print(f"Generating {n_groups} groups...")
    with conn.cursor() as cur:
        with cur.copy("COPY groups (id, group_name, display_name, status, created_at, updated_at) FROM STDIN") as copy:
            for i in range(n_groups):
                id = str(uuid.uuid4())
                name = f"GRP-{fake.word().upper()}-{i+1:05d}"
                groups.append(id)
                copy.write_row((id, name, f"Group {name}", 'active', datetime.now(timezone.utc), datetime.now(timezone.utc)))
        conn.commit()

    # USERS
    users = []
    print(f"Generating {n_users} users...")
    with conn.cursor() as cur:
        with cur.copy("COPY users (id, username, email, display_name, status, created_at, updated_at) FROM STDIN") as copy:
            for i in range(n_users):
                id = str(uuid.uuid4())
                uname = f"usr_{i+1:07d}"
                email = f"{uname}@corp.internal"
                users.append((id, uname))
                copy.write_row((id, uname, email, fake.name(), 'active', datetime.now(timezone.utc), datetime.now(timezone.utc)))
        conn.commit()
                
    # FIREWALLS
    firewalls = []
    print(f"Generating {n_firewalls} firewalls...")
    with conn.cursor() as cur:
        with cur.copy("COPY firewalls (id, hostname, ip_address, status, created_at, updated_at) FROM STDIN") as copy:
            for i in range(n_firewalls):
                id = str(uuid.uuid4())
                firewalls.append(id)
                hostname = f"fw-{i+1:04d}.corp.internal"
                copy.write_row((id, hostname, get_random_rfc1918_ip(rand), 'reachable', datetime.now(timezone.utc), datetime.now(timezone.utc)))
        conn.commit()
                
    # LDAP SERVERS
    ldap_servers = []
    print(f"Generating {n_ldap} ldap servers...")
    with conn.cursor() as cur:
        with cur.copy("COPY ldap_servers (id, firewall_id, profile_name, server_host, status, created_at, updated_at) FROM STDIN") as copy:
            for i in range(n_ldap):
                id = str(uuid.uuid4())
                fw_id = rand.choice(firewalls)
                ldap_servers.append(id)
                copy.write_row((id, fw_id, f"ldap_profile_{i+1}", get_random_rfc1918_ip(rand), 'reachable', datetime.now(timezone.utc), datetime.now(timezone.utc)))
        conn.commit()

    # MEMBERSHIPS
    print(f"Generating {n_memberships} memberships...")
    avg_per_user = max(1, n_memberships // n_users)
    with conn.cursor() as cur:
        with cur.copy("COPY user_group_memberships (user_id, group_id, source, created_at) FROM STDIN") as copy:
            count = 0
            for u_idx, u in enumerate(users):
                if count >= n_memberships:
                    break
                u_id = u[0]
                num_groups = min(len(groups), max(1, avg_per_user + rand.randint(-2, 2)))
                sampled_groups = rand.sample(groups, num_groups)
                for g_id in sampled_groups:
                    copy.write_row((u_id, g_id, 'ldap', datetime.now(timezone.utc)))
                    count += 1
                    if count % 50000 == 0:
                        print(f"  {count}...")
                    if count >= n_memberships:
                        break
        conn.commit()
        
    # IP MAPPINGS
    print(f"Generating IP Mappings...")
    with conn.cursor() as cur:
        with cur.copy("COPY user_ip_mappings (user_id, firewall_id, ip_address, mapped_at, is_current, created_at) FROM STDIN") as copy:
            for u in users:
                if rand.random() > 0.1: # 90% have a mapping
                    u_id = u[0]
                    fw_id = rand.choice(firewalls)
                    copy.write_row((u_id, fw_id, get_random_rfc1918_ip(rand), datetime.now(timezone.utc), True, datetime.now(timezone.utc)))
        conn.commit()

    # FIREWALL GROUP MAPPINGS
    print(f"Generating Firewall Group Mappings...")
    with conn.cursor() as cur:
        with cur.copy("COPY firewall_group_mappings (firewall_id, group_id, status, synced_at, created_at, updated_at) FROM STDIN") as copy:
            for fw_id in firewalls:
                sampled_groups = rand.sample(groups, min(len(groups), 100))
                for g_id in sampled_groups:
                    copy.write_row((fw_id, g_id, 'active', datetime.now(timezone.utc), datetime.now(timezone.utc), datetime.now(timezone.utc)))
        conn.commit()

    # AUTH EVENTS
    print(f"Generating {n_auth_events} auth events...")
    with conn.cursor() as cur:
        with cur.copy("COPY authentication_events (user_id, firewall_id, username_raw, result, occurred_at, created_at) FROM STDIN") as copy:
            for count in range(n_auth_events):
                if rand.random() < 0.95:
                    u_id, uname = rand.choice(users)
                else:
                    u_id = None
                    uname = f"unknown_user_{rand.randint(1, 10000)}"
                
                fw_id = rand.choice(firewalls)
                result = 'success' if rand.random() < 0.9 else 'failure'
                occurred_at = datetime.now(timezone.utc) - timedelta(days=rand.randint(0, 90), hours=rand.randint(0, 23))
                copy.write_row((u_id, fw_id, uname, result, occurred_at, datetime.now(timezone.utc)))
                if (count + 1) % 50000 == 0:
                    print(f"  {count + 1}...")
        conn.commit()

    print("Running failure injection...")
    with conn.cursor() as cur:
        cur.execute("UPDATE firewalls SET status = 'unreachable' WHERE id IN (SELECT id FROM firewalls ORDER BY RANDOM() LIMIT %s)", (max(1, int(n_firewalls * 0.03)),))
        cur.execute("UPDATE ldap_servers SET status = 'unreachable' WHERE id IN (SELECT id FROM ldap_servers ORDER BY RANDOM() LIMIT %s)", (max(1, int(n_ldap * 0.03)),))
        cur.execute("UPDATE ldap_servers SET status = 'tls_error' WHERE id IN (SELECT id FROM ldap_servers ORDER BY RANDOM() LIMIT %s)", (max(1, int(n_ldap * 0.02)),))
        cur.execute("UPDATE users SET status = 'inactive' WHERE id IN (SELECT id FROM users ORDER BY RANDOM() LIMIT %s)", (max(1, int(n_users * 0.05)),))
        cur.execute("UPDATE user_ip_mappings SET mapped_at = NOW() - INTERVAL '10 hours' WHERE id IN (SELECT id FROM user_ip_mappings ORDER BY RANDOM() LIMIT %s)", (max(1, int(n_users * 0.05)),))
        cur.execute("UPDATE firewall_group_mappings SET status = 'stale', synced_at = NOW() - INTERVAL '30 hours' WHERE id IN (SELECT id FROM firewall_group_mappings ORDER BY RANDOM() LIMIT %s)", (max(1, int(n_firewalls * 100 * 0.05)),))
        cur.execute("UPDATE firewall_group_mappings SET status = 'empty' WHERE id IN (SELECT id FROM firewall_group_mappings ORDER BY RANDOM() LIMIT %s)", (max(1, int(n_firewalls * 100 * 0.03)),))
        conn.commit()
    
    print("Done!")

if __name__ == '__main__':
    generate()
