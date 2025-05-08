from datetime import datetime
from app import db

class Subscription(db.Model):
    """User premium subscriptions"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Subscription details
    plan_type = db.Column(db.String(20), nullable=False)  # 'basic', 'premium', 'gold'
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Status
    status = db.Column(db.String(20), default='active')  # 'active', 'cancelled', 'expired'
    
    # Subscription period
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    auto_renew = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Transactions
    transactions = db.relationship('Transaction', backref='subscription', lazy='dynamic')
    
    def is_active(self):
        """Check if subscription is active"""
        now = datetime.utcnow()
        return self.status == 'active' and self.start_date <= now <= self.end_date
    
    def to_dict(self):
        """Convert subscription to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_type': self.plan_type,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'auto_renew': self.auto_renew,
            'is_active': self.is_active(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Subscription {self.id}: {self.plan_type} for {self.user_id}>'

class Transaction(db.Model):
    """Payment transactions"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'))
    
    # Transaction details
    transaction_type = db.Column(db.String(20), nullable=False)  # 'subscription', 'boost', 'promotion', 'credit'
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Payment details
    payment_method = db.Column(db.String(50))
    payment_id = db.Column(db.String(100))
    
    # Status
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed', 'refunded'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert transaction to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount} {self.currency} for {self.transaction_type}>'
