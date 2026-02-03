import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# File to store expenses and budget
EXPENSES_FILE = "expenses.csv"
BUDGET_FILE = "budget_config.csv"

# ============= BUDGET MANAGEMENT FUNCTIONS =============

def init_budget_csv():
    """Initialize budget configuration file if it doesn't exist"""
    if not os.path.exists(BUDGET_FILE) or os.path.getsize(BUDGET_FILE) == 0:
        df = pd.DataFrame(columns=[
            'monthly_salary', 'expense_allocation_type', 'expense_allocation_value',
            'savings_allocation_type', 'savings_allocation_value', 
            'expense_budget', 'expense_balance', 'savings_budget', 'savings_balance',
            'total_spent', 'savings_used_for_expenses', 'last_updated'
        ])
        df.to_csv(BUDGET_FILE, index=False)

def load_budget():
    """Load current budget configuration"""
    init_budget_csv()
    df = pd.read_csv(BUDGET_FILE)
    if df.empty:
        return None
    return df.iloc[0].to_dict()

def save_budget(salary, exp_type, exp_value, sav_type, sav_value):
    """Save budget configuration with validation"""
    # Calculate allocated amounts
    if exp_type == "Percentage":
        expense_budget = (float(exp_value) / 100) * float(salary)
    else:
        expense_budget = float(exp_value)
    
    if sav_type == "Percentage":
        savings_budget = (float(sav_value) / 100) * float(salary)
    else:
        savings_budget = float(sav_value)
    
    # Validate that budget equals salary
    total = expense_budget + savings_budget
    if abs(total - float(salary)) > 0.01:  # Allow small floating point differences
        return False, f"Expense + Savings must equal Salary! Currently: ${total:.2f} vs ${float(salary):.2f}"
    
    # Create new budget configuration
    budget_data = {
        'monthly_salary': [float(salary)],
        'expense_allocation_type': [exp_type.lower()],
        'expense_allocation_value': [float(exp_value)],
        'savings_allocation_type': [sav_type.lower()],
        'savings_allocation_value': [float(sav_value)],
        'expense_budget': [expense_budget],
        'expense_balance': [expense_budget],
        'savings_budget': [savings_budget],
        'savings_balance': [savings_budget],
        'total_spent': [0.0],
        'savings_used_for_expenses': [0.0],
        'last_updated': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    }
    
    df = pd.DataFrame(budget_data)
    df.to_csv(BUDGET_FILE, index=False)
    return True, "Budget saved successfully!"

def update_balances(expense_amount):
    """Update balances after adding an expense"""
    budget = load_budget()
    if not budget:
        return False, "No budget configured!"
    
    expense_balance = float(budget['expense_balance'])
    savings_balance = float(budget['savings_balance'])
    total_spent = float(budget['total_spent'])
    savings_used = float(budget['savings_used_for_expenses'])
    
    # Calculate available funds
    total_available = expense_balance + savings_balance
    
    if expense_amount > total_available:
        return False, f"Insufficient funds! Available: ${total_available:.2f}, Needed: ${expense_amount:.2f}"
    
    # Deduct from expense balance first
    from_expense = 0
    from_savings = 0
    
    if expense_amount <= expense_balance:
        # Entire expense from expense budget
        from_expense = expense_amount
        expense_balance -= expense_amount
    else:
        # Partial from expense, rest from savings
        from_expense = expense_balance
        from_savings = expense_amount - expense_balance
        expense_balance = 0
        savings_balance -= from_savings
        savings_used += from_savings
    
    # Update budget file
    budget_df = pd.read_csv(BUDGET_FILE)
    budget_df.at[0, 'expense_balance'] = expense_balance
    budget_df.at[0, 'savings_balance'] = savings_balance
    budget_df.at[0, 'total_spent'] = total_spent + expense_amount
    budget_df.at[0, 'savings_used_for_expenses'] = savings_used
    budget_df.at[0, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    budget_df.to_csv(BUDGET_FILE, index=False)
    
    return True, (from_expense, from_savings)

def reset_budget():
    """Reset budget to initial state"""
    budget = load_budget()
    if not budget:
        return False
    
    budget_df = pd.read_csv(BUDGET_FILE)
    budget_df.at[0, 'expense_balance'] = budget_df.at[0, 'expense_budget']
    budget_df.at[0, 'savings_balance'] = budget_df.at[0, 'savings_budget']
    budget_df.at[0, 'total_spent'] = 0.0
    budget_df.at[0, 'savings_used_for_expenses'] = 0.0
    budget_df.at[0, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    budget_df.to_csv(BUDGET_FILE, index=False)
    return True

# ============= EXPENSE MANAGEMENT FUNCTIONS =============

def init_csv():
    """Initialize expenses CSV file if it doesn't exist"""
    if not os.path.exists(EXPENSES_FILE) or os.path.getsize(EXPENSES_FILE) == 0:
        df = pd.DataFrame(columns=['Date', 'Category', 'Amount', 'Description', 'From_Savings'])
        df.to_csv(EXPENSES_FILE, index=False)

def load_expenses():
    """Load expenses from CSV"""
    init_csv()
    df = pd.read_csv(EXPENSES_FILE)
    # Add From_Savings column if it doesn't exist (for backward compatibility)
    if 'From_Savings' not in df.columns:
        df['From_Savings'] = 0.0
    return df

def save_expense(date, category, amount, description, from_savings=0.0):
    """Save expense to CSV"""
    df = load_expenses()
    new_expense = pd.DataFrame({
        'Date': [date],
        'Category': [category],
        'Amount': [amount],
        'Description': [description],
        'From_Savings': [from_savings]
    })
    df = pd.concat([df, new_expense], ignore_index=True)
    df.to_csv(EXPENSES_FILE, index=False)

def delete_expense(index):
    """Delete expense and restore budget balances"""
    df = load_expenses()
    if index not in df.index:
        return False, "Expense not found!"
    
    # Get expense details
    expense = df.loc[index]
    amount = float(expense['Amount'])
    from_savings = float(expense.get('From_Savings', 0.0))
    
    # Restore balances if budget exists
    budget = load_budget()
    if budget:
        budget_df = pd.read_csv(BUDGET_FILE)
        
        # Restore expense balance (amount that wasn't from savings)
        from_expense = amount - from_savings
        budget_df.at[0, 'expense_balance'] = min(
            float(budget_df.at[0, 'expense_balance']) + from_expense,
            float(budget_df.at[0, 'expense_budget'])
        )
        
        # Restore savings balance
        budget_df.at[0, 'savings_balance'] = min(
            float(budget_df.at[0, 'savings_balance']) + from_savings,
            float(budget_df.at[0, 'savings_budget'])
        )
        
        # Update totals
        budget_df.at[0, 'total_spent'] = max(0, float(budget_df.at[0, 'total_spent']) - amount)
        budget_df.at[0, 'savings_used_for_expenses'] = max(0, float(budget_df.at[0, 'savings_used_for_expenses']) - from_savings)
        budget_df.at[0, 'last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        budget_df.to_csv(BUDGET_FILE, index=False)
    
    # Delete the expense
    df = df.drop(index)
    df.to_csv(EXPENSES_FILE, index=False)
    return True, "Expense deleted and budget restored!"

# ============= MAIN APPLICATION =============

def main():
    st.set_page_config(page_title="Personal Expense Tracker", page_icon="💰", layout="wide")
    
    st.title("💰 Personal Expense Tracker with Budget Management")
    
    # Load budget
    budget = load_budget()
    
    # ============= SIDEBAR: BUDGET CONFIGURATION =============
    with st.sidebar:
        st.header("💼 Budget Configuration")
        
        with st.expander("⚙️ Setup/Edit Budget", expanded=(budget is None)):
            st.markdown("**Configure Your Monthly Budget**")
            
            # Salary input
            current_salary = budget['monthly_salary'] if budget else 0.0
            salary = st.number_input(
                "Monthly Salary ($)", 
                min_value=0.0, 
                value=float(current_salary),
                step=100.0, 
                format="%.2f"
            )
            
            st.markdown("---")
            
            # Expense allocation
            st.markdown("**💳 Expense Allocation**")
            exp_type = st.radio(
                "Type", 
                ["Percentage", "Fixed Amount"], 
                key="exp_type",
                horizontal=True
            )
            
            if exp_type == "Percentage":
                exp_value = st.number_input(
                    "Expense % of Salary", 
                    min_value=0.0, 
                    max_value=100.0,
                    value=70.0, 
                    step=1.0
                )
                exp_amount = (exp_value / 100) * salary
                st.info(f"💵 Expense Budget: **${exp_amount:.2f}**")
            else:
                exp_value = st.number_input(
                    "Fixed Expense Amount ($)", 
                    min_value=0.0,
                    max_value=float(salary),
                    value=min(3500.0, float(salary)), 
                    step=100.0
                )
                exp_amount = exp_value
            
            st.markdown("---")
            
            # Savings allocation
            st.markdown("**🏦 Savings Allocation**")
            sav_type = st.radio(
                "Type", 
                ["Percentage", "Fixed Amount"], 
                key="sav_type",
                horizontal=True
            )
            
            if sav_type == "Percentage":
                sav_value = st.number_input(
                    "Savings % of Salary", 
                    min_value=0.0, 
                    max_value=100.0,
                    value=30.0, 
                    step=1.0
                )
                sav_amount = (sav_value / 100) * salary
                st.info(f"💰 Savings Budget: **${sav_amount:.2f}**")
            else:
                sav_value = st.number_input(
                    "Fixed Savings Amount ($)", 
                    min_value=0.0,
                    max_value=float(salary),
                    value=min(1500.0, float(salary)), 
                    step=100.0
                )
                sav_amount = sav_value
            
            # Validation display
            total_allocation = exp_amount + sav_amount
            st.markdown("---")
            st.markdown("**📊 Summary**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Allocated", f"${total_allocation:.2f}")
            with col2:
                difference = salary - total_allocation
                st.metric("Difference", f"${difference:.2f}", delta=None)
            
            if abs(difference) > 0.01:
                st.error(f"⚠️ Expense + Savings must equal Salary!")
            else:
                st.success("✅ Budget balanced!")
            
            # Save budget button
            if st.button("💾 Save Budget", type="primary", use_container_width=True):
                success, message = save_budget(salary, exp_type, exp_value, sav_type, sav_value)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        # Reset budget option
        if budget:
            with st.expander("🔄 Reset Budget"):
                st.warning("This will reset all balances to initial budget values and keep total spent.")
                if st.button("Reset Budget Balances", type="secondary", use_container_width=True):
                    if reset_budget():
                        st.success("Budget reset successfully!")
                        st.rerun()
        
        st.markdown("---")
        
        # ============= SIDEBAR: ADD EXPENSE =============
        st.header("➕ Add New Expense")
        
        if not budget:
            st.warning("⚠️ Please configure your budget first!")
        else:
            date = st.date_input("Date", datetime.now())
            category = st.selectbox(
                "Category",
                ["Food", "Transportation", "Shopping", "Bills", "Entertainment", "Health", "Other"]
            )
            amount = st.number_input("Amount ($)", min_value=0.0, step=0.01, format="%.2f")
            description = st.text_input("Description")
            
            # Show available balance
            available = float(budget['expense_balance']) + float(budget['savings_balance'])
            st.info(f"💵 Available: ${available:.2f}")
            
            if st.button("Add Expense", type="primary", use_container_width=True):
                if amount > 0:
                    success, result = update_balances(amount)
                    if success:
                        from_expense, from_savings = result
                        save_expense(str(date), category, amount, description, from_savings)
                        
                        if from_savings > 0:
                            st.warning(f"⚠️ ${from_expense:.2f} from expense budget + ${from_savings:.2f} from savings!")
                        else:
                            st.success("✅ Expense added successfully!")
                        st.rerun()
                    else:
                        st.error(result)
                else:
                    st.error("Please enter a valid amount")
    
    # ============= MAIN CONTENT =============
    
    # Budget Dashboard (if budget configured)
    if budget:
        st.markdown("### 📊 Budget Overview")
        
        expense_used = float(budget['expense_budget']) - float(budget['expense_balance'])
        expense_percent = (expense_used / float(budget['expense_budget']) * 100) if float(budget['expense_budget']) > 0 else 0
        
        savings_used = float(budget['savings_budget']) - float(budget['savings_balance'])
        savings_percent = (savings_used / float(budget['savings_budget']) * 100) if float(budget['savings_budget']) > 0 else 0
        
        # Warnings
        if expense_percent >= 80 and float(budget['expense_balance']) > 0:
            st.warning(f"⚠️ **Budget Alert**: You've used {expense_percent:.1f}% of your expense budget!")
        
        if float(budget['savings_used_for_expenses']) > 0:
            st.error(f"🚨 **Savings Alert**: ${float(budget['savings_used_for_expenses']):.2f} has been taken from your savings to cover expenses!")
        
        # Metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("💰 Monthly Salary", f"${float(budget['monthly_salary']):.2f}")
        
        with col2:
            st.metric("💳 Expense Budget", f"${float(budget['expense_budget']):.2f}")
        
        with col3:
            delta_color = "normal" if float(budget['expense_balance']) > 0 else "off"
            st.metric(
                "💵 Expense Balance", 
                f"${float(budget['expense_balance']):.2f}",
                delta=f"{expense_percent:.0f}% used"
            )
        
        with col4:
            st.metric("🏦 Savings Budget", f"${float(budget['savings_budget']):.2f}")
        
        with col5:
            st.metric(
                "💎 Savings Balance", 
                f"${float(budget['savings_balance']):.2f}",
                delta=f"{savings_percent:.0f}% used"
            )
        
        with col6:
            st.metric("📊 Total Spent", f"${float(budget['total_spent']):.2f}")
        
        # Progress bars
        st.markdown("**Budget Utilization**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Expense Budget**")
            st.progress(min(expense_percent / 100, 1.0))
            st.caption(f"Used: ${expense_used:.2f} / ${float(budget['expense_budget']):.2f}")
        
        with col2:
            st.markdown("**Savings Budget**")
            st.progress(min(savings_percent / 100, 1.0))
            st.caption(f"Used: ${savings_used:.2f} / ${float(budget['savings_budget']):.2f}")
        
        st.markdown("---")
    
    # Load expenses
    df = load_expenses()
    
    # Main content
    if not df.empty:
        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 All Expenses", "📈 Analytics"])
        
        with tab1:
            # Category breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Expenses by Category")
                category_sum = df.groupby('Category')['Amount'].sum().reset_index()
                fig_pie = px.pie(category_sum, values='Amount', names='Category', 
                                title='Category Distribution',
                                color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.subheader("Recent Expenses")
                recent_df = df.tail(5)[['Date', 'Category', 'Amount', 'Description']].copy()
                st.dataframe(recent_df, use_container_width=True, hide_index=True)
        
        with tab2:
            st.subheader("All Expenses")
            
            # Filter options
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                selected_categories = st.multiselect(
                    "Filter by Category",
                    options=df['Category'].unique(),
                    default=df['Category'].unique()
                )
            
            filtered_df = df[df['Category'].isin(selected_categories)]
            
            # Display expenses with delete option
            st.markdown("---")
            for idx, row in filtered_df.iterrows():
                col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1.5, 1.5, 2.5, 1.5, 0.5])
                with col1:
                    st.write(f"**{row['Date']}**")
                with col2:
                    st.write(row['Category'])
                with col3:
                    st.write(f"${row['Amount']:.2f}")
                with col4:
                    st.write(row['Description'])
                with col5:
                    if row['From_Savings'] > 0:
                        st.write(f"🏦 ${row['From_Savings']:.2f}")
                    else:
                        st.write("")
                with col6:
                    if st.button("🗑️", key=f"delete_{idx}"):
                        success, message = delete_expense(idx)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        st.rerun()
            
            st.markdown("---")
            
            # Download option
            st.download_button(
                label="📥 Download CSV",
                data=filtered_df.to_csv(index=False),
                file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with tab3:
            st.subheader("Expense Analytics")
            
            # Convert date to datetime for better plotting
            df_copy = df.copy()
            df_copy['Date'] = pd.to_datetime(df_copy['Date'])
            
            # Spending trend over time
            daily_expenses = df_copy.groupby('Date')['Amount'].sum().reset_index()
            fig_line = px.line(daily_expenses, x='Date', y='Amount', 
                             title='Spending Trend Over Time',
                             labels={'Amount': 'Total Amount ($)'},
                             markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Category comparison
            category_stats = df_copy.groupby('Category')['Amount'].agg(['sum', 'mean', 'count']).reset_index()
            category_stats.columns = ['Category', 'Total', 'Average', 'Count']
            category_stats = category_stats.sort_values('Total', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Category Statistics")
                st.dataframe(
                    category_stats.style.format({'Total': '${:.2f}', 'Average': '${:.2f}'}),
                    use_container_width=True,
                    hide_index=True
                )
            
            with col2:
                st.subheader("Spending by Category")
                fig_bar = px.bar(category_stats, x='Category', y='Total',
                               title='Total Spending by Category',
                               color='Total',
                               color_continuous_scale='Blues')
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("📝 No expenses recorded yet. Add your first expense using the sidebar!")

if __name__ == "__main__":
    main()
