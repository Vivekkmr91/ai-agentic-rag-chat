"""
Sample Database Creation Utility
Creates a sample SQLite database with realistic data for testing the RAG system
"""
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
import json

class SampleDatabaseCreator:
    """Creates a sample database with realistic business data"""
    
    def __init__(self, db_path: str = "sample_business.db"):
        self.db_path = Path(db_path)
        self.conn = None
        
    def create_database(self):
        """Create the complete sample database"""
        print(f"Creating sample database: {self.db_path}")
        
        # Remove existing database
        if self.db_path.exists():
            self.db_path.unlink()
        
        # Create connection
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            # Create tables
            self._create_tables()
            
            # Insert sample data
            self._insert_sample_data()
            
            # Commit changes
            self.conn.commit()
            
            print(f"✅ Sample database created successfully at {self.db_path}")
            self._print_database_stats()
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error creating database: {e}")
            raise
        
        finally:
            if self.conn:
                self.conn.close()
    
    def _create_tables(self):
        """Create all database tables"""
        
        # Users table
        self.conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                date_of_birth DATE,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'active',
                city VARCHAR(100),
                country VARCHAR(100) DEFAULT 'United States'
            )
        """)
        
        # Products table
        self.conn.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                cost DECIMAL(10, 2) NOT NULL,
                stock_quantity INTEGER DEFAULT 0,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                supplier_id INTEGER,
                weight_kg DECIMAL(5, 2),
                dimensions VARCHAR(50)
            )
        """)
        
        # Orders table
        self.conn.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_amount DECIMAL(10, 2) NOT NULL,
                tax_amount DECIMAL(10, 2) DEFAULT 0,
                shipping_amount DECIMAL(10, 2) DEFAULT 0,
                status VARCHAR(50) DEFAULT 'pending',
                shipping_address TEXT,
                billing_address TEXT,
                payment_method VARCHAR(50),
                tracking_number VARCHAR(100),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Order Items table
        self.conn.execute("""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        # Reviews table
        self.conn.execute("""
            CREATE TABLE reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                title VARCHAR(255),
                review_text TEXT,
                review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                helpful_votes INTEGER DEFAULT 0,
                verified_purchase BOOLEAN DEFAULT 0,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Suppliers table
        self.conn.execute("""
            CREATE TABLE suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name VARCHAR(255) NOT NULL,
                contact_person VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(20),
                address TEXT,
                city VARCHAR(100),
                country VARCHAR(100),
                established_year INTEGER,
                rating DECIMAL(2, 1)
            )
        """)
        
        # Sales Analytics table (aggregated data)
        self.conn.execute("""
            CREATE TABLE sales_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                total_sales DECIMAL(12, 2) DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                unique_customers INTEGER DEFAULT 0,
                avg_order_value DECIMAL(10, 2) DEFAULT 0,
                top_selling_category VARCHAR(100),
                region VARCHAR(100)
            )
        """)
        
        # Create indexes for better performance
        self.conn.execute("CREATE INDEX idx_users_email ON users(email)")
        self.conn.execute("CREATE INDEX idx_orders_user_id ON orders(user_id)")
        self.conn.execute("CREATE INDEX idx_orders_date ON orders(order_date)")
        self.conn.execute("CREATE INDEX idx_order_items_order_id ON order_items(order_id)")
        self.conn.execute("CREATE INDEX idx_order_items_product_id ON order_items(product_id)")
        self.conn.execute("CREATE INDEX idx_reviews_product_id ON reviews(product_id)")
        self.conn.execute("CREATE INDEX idx_products_category ON products(category)")
    
    def _insert_sample_data(self):
        """Insert realistic sample data"""
        
        # Insert suppliers first
        suppliers = [
            ("TechCorp Industries", "John Smith", "john@techcorp.com", "+1-555-0101", "123 Tech Ave, San Jose, CA", "San Jose", "United States", 1995, 4.5),
            ("Global Electronics", "Maria Rodriguez", "maria@globalelec.com", "+1-555-0102", "456 Circuit St, Austin, TX", "Austin", "United States", 2001, 4.2),
            ("Innovation Labs", "David Chen", "david@innovlabs.com", "+1-555-0103", "789 Innovation Blvd, Seattle, WA", "Seattle", "United States", 2010, 4.7),
            ("Premium Parts Co", "Sarah Johnson", "sarah@premiumparts.com", "+1-555-0104", "321 Quality Rd, Boston, MA", "Boston", "United States", 1988, 4.3),
            ("Future Systems", "Alex Kim", "alex@futuresys.com", "+1-555-0105", "654 Future Way, Denver, CO", "Denver", "United States", 2015, 4.6)
        ]
        
        self.conn.executemany("""
            INSERT INTO suppliers (company_name, contact_person, email, phone, address, city, country, established_year, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, suppliers)
        
        # Insert users
        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa", "William", "Emma", 
                      "James", "Olivia", "Benjamin", "Sophia", "Alexander", "Isabella", "Daniel", "Mia", "Matthew", "Charlotte"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                     "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
        cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
        
        users_data = []
        for i in range(1, 501):  # 500 users
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email = f"{first_name.lower()}.{last_name.lower()}.{i}@email.com"
            phone = f"+1-555-{random.randint(1000, 9999)}"
            birth_date = datetime(1960, 1, 1) + timedelta(days=random.randint(0, 20000))
            reg_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1400))
            status = random.choice(["active", "active", "active", "inactive"])  # 75% active
            city = random.choice(cities)
            
            users_data.append((email, first_name, last_name, phone, birth_date.date(), reg_date, status, city, "United States"))
        
        self.conn.executemany("""
            INSERT INTO users (email, first_name, last_name, phone, date_of_birth, registration_date, status, city, country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, users_data)
        
        # Insert products
        categories = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books", "Beauty", "Automotive", "Toys"]
        product_names = {
            "Electronics": ["Smartphone", "Laptop", "Tablet", "Headphones", "Smart Watch", "Camera", "Speaker", "Monitor"],
            "Clothing": ["T-Shirt", "Jeans", "Dress", "Jacket", "Shoes", "Hat", "Sweater", "Shorts"],
            "Home & Garden": ["Coffee Maker", "Blender", "Vacuum", "Plant Pot", "Lamp", "Cushion", "Tool Set", "Garden Hose"],
            "Sports": ["Running Shoes", "Yoga Mat", "Basketball", "Tennis Racket", "Bicycle", "Helmet", "Water Bottle", "Dumbbells"],
            "Books": ["Fiction Novel", "Cookbook", "Biography", "Self-Help", "Science Fiction", "Mystery", "Romance", "History"],
            "Beauty": ["Lipstick", "Foundation", "Mascara", "Perfume", "Face Cream", "Shampoo", "Body Lotion", "Nail Polish"],
            "Automotive": ["Car Charger", "Dash Cam", "Floor Mats", "Air Freshener", "Phone Mount", "Jumper Cables", "Tire Gauge", "Car Cover"],
            "Toys": ["Action Figure", "Board Game", "Puzzle", "Doll", "Building Blocks", "RC Car", "Art Set", "Musical Toy"]
        }
        
        products_data = []
        product_id = 1
        for category in categories:
            for base_name in product_names[category]:
                for variant in ["Pro", "Deluxe", "Standard", "Premium", "Basic"]:
                    name = f"{base_name} {variant}"
                    description = f"High-quality {base_name.lower()} in the {category.lower()} category. {variant} edition with excellent features."
                    
                    base_price = random.uniform(10, 500)
                    price = round(base_price * random.uniform(0.8, 1.5), 2)
                    cost = round(price * random.uniform(0.4, 0.7), 2)
                    stock = random.randint(0, 100)
                    supplier_id = random.randint(1, 5)
                    weight = round(random.uniform(0.1, 5.0), 2)
                    dimensions = f"{random.randint(5, 50)}x{random.randint(5, 50)}x{random.randint(5, 50)}cm"
                    is_active = random.choice([1, 1, 1, 0])  # 75% active
                    
                    created_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1200))
                    
                    products_data.append((name, description, category, price, cost, stock, created_date, is_active, supplier_id, weight, dimensions))
                    product_id += 1
                    
                    if product_id > 200:  # Limit to 200 products
                        break
                if product_id > 200:
                    break
            if product_id > 200:
                break
        
        self.conn.executemany("""
            INSERT INTO products (name, description, category, price, cost, stock_quantity, created_date, is_active, supplier_id, weight_kg, dimensions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, products_data)
        
        # Insert orders and order items
        orders_data = []
        order_items_data = []
        
        for order_id in range(1, 1001):  # 1000 orders
            user_id = random.randint(1, 500)
            order_date = datetime(2021, 1, 1) + timedelta(days=random.randint(0, 1095))  # 3 years of orders
            
            # Generate 1-5 items per order
            num_items = random.randint(1, 5)
            total_amount = 0
            
            for _ in range(num_items):
                product_id = random.randint(1, min(200, product_id - 1))
                quantity = random.randint(1, 3)
                
                # Get product price (simplified - in reality you'd query the product)
                unit_price = round(random.uniform(10, 500), 2)
                item_total = round(unit_price * quantity, 2)
                total_amount += item_total
                
                order_items_data.append((order_id, product_id, quantity, unit_price, item_total))
            
            tax_amount = round(total_amount * 0.08, 2)  # 8% tax
            shipping_amount = 0 if total_amount > 50 else 9.99
            final_total = total_amount + tax_amount + shipping_amount
            
            status = random.choice(["pending", "processing", "shipped", "delivered", "cancelled"])
            payment_method = random.choice(["credit_card", "debit_card", "paypal", "apple_pay"])
            tracking = f"TRK{random.randint(100000, 999999)}" if status in ["shipped", "delivered"] else None
            
            address = f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm', 'Park'])} {random.choice(['St', 'Ave', 'Rd', 'Blvd'])}, {random.choice(cities)}, {random.choice(['CA', 'NY', 'TX', 'FL', 'IL'])}"
            
            orders_data.append((user_id, order_date, final_total, tax_amount, shipping_amount, status, address, address, payment_method, tracking))
        
        self.conn.executemany("""
            INSERT INTO orders (user_id, order_date, total_amount, tax_amount, shipping_amount, status, shipping_address, billing_address, payment_method, tracking_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, orders_data)
        
        self.conn.executemany("""
            INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
        """, order_items_data)
        
        # Insert reviews
        reviews_data = []
        review_titles = [
            "Great product!", "Love it!", "Good value", "Excellent quality", "Highly recommend",
            "Not bad", "Could be better", "Disappointing", "Amazing!", "Perfect for my needs",
            "Fast shipping", "Good customer service", "Will buy again", "Exactly as described"
        ]
        
        review_texts = [
            "This product exceeded my expectations. Great quality and fast delivery.",
            "Really happy with this purchase. Would definitely recommend to others.",
            "Good product for the price. Shipping was quick and packaging was secure.",
            "Excellent quality and great customer service. Very satisfied with my purchase.",
            "Product works as expected. No complaints. Will consider buying again.",
            "Decent product but could use some improvements. Overall satisfied.",
            "Not exactly what I expected but it works fine for what I need.",
            "Outstanding product! Exactly what I was looking for. Highly recommended."
        ]
        
        for _ in range(2000):  # 2000 reviews
            product_id = random.randint(1, min(200, product_id - 1))
            user_id = random.randint(1, 500)
            rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]  # Skew towards higher ratings
            title = random.choice(review_titles)
            text = random.choice(review_texts)
            review_date = datetime(2021, 6, 1) + timedelta(days=random.randint(0, 900))
            helpful_votes = random.randint(0, 50)
            verified = random.choice([0, 1])
            
            reviews_data.append((product_id, user_id, rating, title, text, review_date, helpful_votes, verified))
        
        self.conn.executemany("""
            INSERT INTO reviews (product_id, user_id, rating, title, review_text, review_date, helpful_votes, verified_purchase)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, reviews_data)
        
        # Insert sales analytics (aggregated daily data)
        analytics_data = []
        start_date = datetime(2021, 1, 1).date()
        end_date = datetime(2024, 1, 1).date()
        
        current_date = start_date
        while current_date < end_date:
            total_sales = round(random.uniform(5000, 25000), 2)
            total_orders = random.randint(20, 100)
            unique_customers = random.randint(15, 80)
            avg_order_value = round(total_sales / total_orders, 2) if total_orders > 0 else 0
            top_category = random.choice(categories)
            region = random.choice(["North", "South", "East", "West", "Central"])
            
            analytics_data.append((current_date, total_sales, total_orders, unique_customers, avg_order_value, top_category, region))
            current_date += timedelta(days=1)
        
        self.conn.executemany("""
            INSERT INTO sales_analytics (date, total_sales, total_orders, unique_customers, avg_order_value, top_selling_category, region)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, analytics_data)
    
    def _print_database_stats(self):
        """Print database statistics"""
        stats = {}
        tables = ["users", "products", "orders", "order_items", "reviews", "suppliers", "sales_analytics"]
        
        for table in tables:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            stats[table] = count
        
        print("\n📊 Database Statistics:")
        print("-" * 30)
        for table, count in stats.items():
            print(f"{table:.<20} {count:>8,}")
        print("-" * 30)
        print(f"{'Total Records':.<20} {sum(stats.values()):>8,}")

def main():
    """Create the sample database"""
    creator = SampleDatabaseCreator("sample_business.db")
    creator.create_database()
    
    # Create a smaller test database too
    creator_small = SampleDatabaseCreator("test_small.db")
    # Modify for smaller dataset (you could customize this)
    creator_small.create_database()
    
    print("\n🎉 Sample databases created successfully!")
    print("📁 Files created:")
    print("  - sample_business.db (Full dataset)")
    print("  - test_small.db (Test dataset)")
    print("\n💡 You can now connect to these databases in the RAG system!")

if __name__ == "__main__":
    main()