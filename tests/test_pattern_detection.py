"""Test pattern detection functionality."""

import pytest
import tempfile
from pathlib import Path

from velocitytree.code_analysis import CodeAnalyzer
from velocitytree.code_analysis.models import PatternType


class TestPatternDetection:
    """Test pattern detection in code analysis."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a code analyzer instance."""
        return CodeAnalyzer()
    
    def test_singleton_pattern_detection(self, analyzer):
        """Test detection of Singleton design pattern."""
        code = '''
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            singleton_patterns = [p for p in result.patterns 
                                if p.name == "Singleton"]
            assert len(singleton_patterns) > 0
            assert singleton_patterns[0].pattern_type == PatternType.DESIGN_PATTERN
            assert singleton_patterns[0].confidence >= 0.8
        finally:
            temp_path.unlink()
    
    def test_factory_pattern_detection(self, analyzer):
        """Test detection of Factory design pattern."""
        code = '''
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

class AnimalFactory:
    def create_animal(self, animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()
        return None
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            factory_patterns = [p for p in result.patterns 
                              if p.name == "Factory"]
            assert len(factory_patterns) > 0
            assert factory_patterns[0].pattern_type == PatternType.DESIGN_PATTERN
        finally:
            temp_path.unlink()
    
    def test_observer_pattern_detection(self, analyzer):
        """Test detection of Observer design pattern."""
        code = '''
class Subject:
    def __init__(self):
        self._observers = []
    
    def attach(self, observer):
        self._observers.append(observer)
    
    def detach(self, observer):
        self._observers.remove(observer)
    
    def notify(self):
        for observer in self._observers:
            observer.update(self)

class Observer:
    def update(self, subject):
        pass
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            observer_patterns = [p for p in result.patterns 
                               if p.name == "Observer"]
            assert len(observer_patterns) > 0
            assert observer_patterns[0].pattern_type == PatternType.DESIGN_PATTERN
            assert observer_patterns[0].confidence >= 0.8
        finally:
            temp_path.unlink()
    
    def test_god_class_anti_pattern(self, analyzer):
        """Test detection of God Class anti-pattern."""
        code = '''
class GodClass:
    def __init__(self):
        ''' + '\n'.join([f'self.attr{i} = None' for i in range(20)]) + '''
    
    ''' + '\n    '.join([f'def method{i}(self): pass' for i in range(25)]) + '''
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            god_class_patterns = [p for p in result.patterns 
                                if p.name == "God Class"]
            assert len(god_class_patterns) > 0
            assert god_class_patterns[0].pattern_type == PatternType.ANTI_PATTERN
            
            metadata = god_class_patterns[0].metadata
            assert metadata['method_count'] >= 25
            assert metadata['attribute_count'] >= 20
        finally:
            temp_path.unlink()
    
    def test_long_parameter_list_anti_pattern(self, analyzer):
        """Test detection of Long Parameter List anti-pattern."""
        code = '''
def process_data(param1, param2, param3, param4, param5, param6, param7):
    return param1 + param2

class DataProcessor:
    def complex_method(self, a, b, c, d, e, f, g, h):
        return a * b
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            long_param_patterns = [p for p in result.patterns 
                                 if p.name == "Long Parameter List"]
            assert len(long_param_patterns) >= 2
            assert all(p.pattern_type == PatternType.ANTI_PATTERN 
                      for p in long_param_patterns)
        finally:
            temp_path.unlink()
    
    def test_duplicate_code_detection(self, analyzer):
        """Test detection of Duplicate Code smell."""
        code = '''
def calculate_total(items):
    total = 0
    for item in items:
        if item > 0:
            total += item
    return total

def sum_positive(numbers):
    total = 0
    for item in numbers:
        if item > 0:
            total += item
    return total
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            duplicate_patterns = [p for p in result.patterns 
                                if p.name == "Duplicate Code"]
            assert len(duplicate_patterns) > 0
            assert duplicate_patterns[0].pattern_type == PatternType.CODE_SMELL
            assert duplicate_patterns[0].confidence > 0.7
        finally:
            temp_path.unlink()
    
    def test_strategy_pattern_detection(self, analyzer):
        """Test detection of Strategy design pattern."""
        code = '''
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount):
        pass

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount):
        return f"Paid {amount} with credit card"

class PayPalPayment(PaymentStrategy):
    def pay(self, amount):
        return f"Paid {amount} with PayPal"

class ShoppingCart:
    def __init__(self):
        self.payment_strategy = None
    
    def set_payment_strategy(self, strategy: PaymentStrategy):
        self.payment_strategy = strategy
    
    def checkout(self, total):
        return self.payment_strategy.pay(total)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            strategy_patterns = [p for p in result.patterns 
                               if p.name == "Strategy"]
            assert len(strategy_patterns) > 0
            assert strategy_patterns[0].pattern_type == PatternType.DESIGN_PATTERN
            
            metadata = strategy_patterns[0].metadata
            assert metadata['interface'] == 'PaymentStrategy'
            assert 'CreditCardPayment' in metadata['implementations']
            assert 'PayPalPayment' in metadata['implementations']
        finally:
            temp_path.unlink()
    
    def test_decorator_pattern_detection(self, analyzer):
        """Test detection of Decorator design pattern."""
        code = '''
def timing_decorator(func):
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start} seconds")
        return result
    return wrapper

@timing_decorator
def slow_function():
    import time
    time.sleep(1)
    return "Done"

class Component:
    def operation(self):
        pass

class ConcreteComponent(Component):
    def operation(self):
        return "Basic operation"

class Decorator(Component):
    def __init__(self, component):
        self._component = component
    
    def operation(self):
        return self._component.operation()
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            decorator_patterns = [p for p in result.patterns 
                                if p.name == "Decorator"]
            assert len(decorator_patterns) >= 2  # Function decorator and structural
            
            # Check both types of decorators
            has_function_decorator = any(
                p.metadata.get('type') == 'function_decorator' 
                for p in decorator_patterns
            )
            has_structural_decorator = any(
                p.metadata.get('type') == 'structural_decorator' 
                for p in decorator_patterns
            )
            
            assert has_function_decorator
            assert has_structural_decorator
        finally:
            temp_path.unlink()
    
    def test_magic_numbers_detection(self, analyzer):
        """Test detection of Magic Numbers code smell."""
        code = '''
def calculate_area(radius):
    return 3.14159 * radius * radius  # Magic number

def process_data(data):
    if len(data) > 42:  # Magic number
        return data[:42]
    return data

# These should not be detected as magic numbers
CONSTANT_VALUE = 100
zero_value = 0
one_value = 1
two_value = 2
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            magic_patterns = [p for p in result.patterns 
                            if p.name == "Magic Numbers"]
            assert len(magic_patterns) >= 2
            
            # Check that specific numbers were detected
            values = [p.metadata['value'] for p in magic_patterns]
            assert any('3.14159' in v for v in values)
            assert any('42' in v for v in values)
        finally:
            temp_path.unlink()
    
    def test_feature_envy_detection(self, analyzer):
        """Test detection of Feature Envy code smell."""
        code = '''
class Customer:
    def __init__(self):
        self.name = ""
        self.address = ""
        self.phone = ""

class Order:
    def __init__(self, customer):
        self.customer = customer
        self.items = []
    
    def get_customer_details(self):
        # This method uses customer more than self
        details = f"Name: {self.customer.name}"
        details += f"\\nAddress: {self.customer.address}"
        details += f"\\nPhone: {self.customer.phone}"
        if self.customer.name.startswith("VIP"):
            details += "\\nVIP Customer"
        return details
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            envy_patterns = [p for p in result.patterns 
                           if p.name == "Feature Envy"]
            assert len(envy_patterns) > 0
            assert envy_patterns[0].pattern_type == PatternType.CODE_SMELL
            
            metadata = envy_patterns[0].metadata
            assert metadata['method'] == 'get_customer_details'
            assert metadata['envied_object'] == 'customer'
        finally:
            temp_path.unlink()
    
    def test_data_clump_detection(self, analyzer):
        """Test detection of Data Clump code smell."""
        code = '''
def process_order(customer_name, customer_email, customer_phone, order_id):
    pass

def send_notification(customer_name, customer_email, customer_phone, message):
    pass

def update_customer(customer_name, customer_email, customer_phone, updates):
    pass

class CustomerService:
    def create_customer(self, customer_name, customer_email, customer_phone):
        pass
    
    def validate_customer(self, customer_name, customer_email, customer_phone):
        pass
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            clump_patterns = [p for p in result.patterns 
                            if p.name == "Data Clump"]
            assert len(clump_patterns) > 0
            assert clump_patterns[0].pattern_type == PatternType.CODE_SMELL
            
            metadata = clump_patterns[0].metadata
            # Check that customer data parameters were detected as clump
            params = metadata['parameters']
            assert 'customer_name' in params
            assert 'customer_email' in params
            assert 'customer_phone' in params
            assert len(metadata['occurrences']) >= 3
        finally:
            temp_path.unlink()
    
    def test_pattern_detection_in_complex_code(self, analyzer):
        """Test pattern detection in more complex, realistic code."""
        code = '''
from abc import ABC, abstractmethod
import logging

class DatabaseConnection(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def execute_query(self, query):
        pass

class MySQLConnection(DatabaseConnection):
    def connect(self):
        return "MySQL connected"
    
    def execute_query(self, query):
        return f"MySQL: {query}"

class PostgreSQLConnection(DatabaseConnection):
    def connect(self):
        return "PostgreSQL connected"
    
    def execute_query(self, query):
        return f"PostgreSQL: {query}"

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.connection_strategy = None
        self.logger = logging.getLogger(__name__)
    
    def set_connection_strategy(self, strategy: DatabaseConnection):
        self.connection_strategy = strategy
    
    def execute(self, query):
        if not self.connection_strategy:
            raise ValueError("No connection strategy set")
        
        result = self.connection_strategy.execute_query(query)
        self.logger.info(f"Executed query: {query}")
        return result

# This is a god class with too many responsibilities
class UserService:
    def __init__(self):
        self.users = {}
        self.roles = {}
        self.permissions = {}
        self.sessions = {}
        self.audit_log = []
        self.email_queue = []
        self.notification_queue = []
        self.cache = {}
        self.validators = {}
        self.formatters = {}
    
    def create_user(self, username, email, password): pass
    def update_user(self, user_id, data): pass
    def delete_user(self, user_id): pass
    def get_user(self, user_id): pass
    def list_users(self): pass
    def authenticate_user(self, username, password): pass
    def authorize_user(self, user_id, permission): pass
    def create_session(self, user_id): pass
    def validate_session(self, session_id): pass
    def end_session(self, session_id): pass
    def assign_role(self, user_id, role): pass
    def remove_role(self, user_id, role): pass
    def grant_permission(self, role, permission): pass
    def revoke_permission(self, role, permission): pass
    def send_email(self, user_id, subject, body): pass
    def send_notification(self, user_id, message): pass
    def log_action(self, user_id, action): pass
    def cache_user(self, user_id, data): pass
    def invalidate_cache(self, user_id): pass
    def validate_email(self, email): pass
    def validate_password(self, password): pass
    def format_user_data(self, user): pass
    def export_users(self, format): pass
    def import_users(self, data): pass
    def backup_data(self): pass
    def restore_data(self, backup): pass
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            # Should detect multiple patterns
            pattern_names = {p.name for p in result.patterns}
            
            # Design patterns
            assert "Singleton" in pattern_names
            assert "Strategy" in pattern_names
            
            # Anti-patterns
            assert "God Class" in pattern_names
            
            # Specific checks
            god_class = next(p for p in result.patterns if p.name == "God Class")
            assert god_class.location.line_start > 0  # UserService location
            assert god_class.metadata['method_count'] >= 20
            
            singleton = next(p for p in result.patterns if p.name == "Singleton")
            assert "DatabaseManager" in singleton.description or singleton.location.line_start > 0
            
            strategy = next(p for p in result.patterns if p.name == "Strategy")
            assert strategy.metadata['interface'] == 'DatabaseConnection'
            assert len(strategy.metadata['implementations']) >= 2
        finally:
            temp_path.unlink()