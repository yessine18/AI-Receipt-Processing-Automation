"""
Discord Bot for Receipt Processing
Integrates with existing FastAPI backend
"""
import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import io
from typing import Optional
import logging

# Local imports
from database import Database
from api_client import APIClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

# Bot configuration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Initialize API client and database
api_client = APIClient(API_BASE_URL)
db = Database()

# User sessions: Discord user ID -> API token
user_sessions = {}

# Receipt cache: User ID -> {number: receipt_id}
# Maps short numbers like #1, #2 to full receipt UUIDs for easy reference
user_receipt_cache = {}


def resolve_receipt_id(user_id: str, receipt_ref: str) -> str:
    """
    Resolve a receipt reference (number or UUID) to a full UUID
    
    Args:
        user_id: Discord user ID
        receipt_ref: Either a number (e.g., "1", "#1") or full UUID
    
    Returns:
        Full receipt UUID or the original reference if not found
    """
    # Remove # if present
    receipt_ref = receipt_ref.strip().lstrip('#')
    
    # Try to parse as integer (short number)
    try:
        num = int(receipt_ref)
        if user_id in user_receipt_cache and num in user_receipt_cache[user_id]:
            return user_receipt_cache[user_id][num]
    except ValueError:
        pass
    
    # Return as-is (assume it's already a UUID)
    return receipt_ref


def cache_receipts(user_id: str, receipts: list):
    """
    Cache receipts with short numbers for easy reference
    
    Args:
        user_id: Discord user ID
        receipts: List of receipt dictionaries
    """
    if user_id not in user_receipt_cache:
        user_receipt_cache[user_id] = {}
    
    for idx, receipt in enumerate(receipts, 1):
        user_receipt_cache[user_id][idx] = receipt['id']


@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')
    
    # Start scheduled tasks if enabled
    if os.getenv('ENABLE_SCHEDULED_REPORTS', 'false').lower() == 'true':
        weekly_report.start()
        logger.info('Scheduled reports enabled')


@bot.event
async def on_message(message):
    """Handle incoming messages"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Check if message has image attachments
    if message.attachments:
        for attachment in message.attachments:
            # Check if it's an image
            if attachment.content_type and attachment.content_type.startswith('image/'):
                await process_receipt_image(message, attachment)
                return
    
    # Process commands
    await bot.process_commands(message)


async def process_receipt_image(message, attachment):
    """Process receipt image from Discord"""
    try:
        # Send processing message
        processing_msg = await message.reply('📸 Processing your receipt... Please wait.')
        
        # Check if user is logged in
        user_id = str(message.author.id)
        if user_id not in user_sessions:
            await processing_msg.edit(content='❌ Please login first using `/login` command!')
            return
        
        token = user_sessions[user_id]
        
        # Download image
        image_data = await attachment.read()
        
        # Upload to API
        result = await api_client.upload_receipt(
            image_data=image_data,
            filename=attachment.filename,
            token=token
        )
        
        if result['success']:
            receipt_data = result['data']
            
            # Create embed with receipt information
            embed = discord.Embed(
                title='✅ Receipt Processed Successfully!',
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name='Vendor',
                value=receipt_data.get('vendor', 'Unknown'),
                inline=True
            )
            
            embed.add_field(
                name='Date',
                value=receipt_data.get('date', 'N/A'),
                inline=True
            )
            
            embed.add_field(
                name='Total Amount',
                value=f"{receipt_data.get('currency', 'USD')} {receipt_data.get('total_amount', '0.00')}",
                inline=True
            )
            
            if receipt_data.get('category'):
                embed.add_field(
                    name='Category',
                    value=receipt_data.get('category'),
                    inline=True
                )
            
            if receipt_data.get('tax_amount'):
                embed.add_field(
                    name='Tax',
                    value=f"{receipt_data.get('currency', 'USD')} {receipt_data.get('tax_amount')}",
                    inline=True
                )
            
            embed.add_field(
                name='Receipt ID',
                value=f"`{receipt_data.get('id')}`",
                inline=False
            )
            
            embed.set_footer(text=f'Requested by {message.author.display_name}')
            
            await processing_msg.edit(content=None, embed=embed)
            
        else:
            error_msg = result.get('error', 'Unknown error occurred')
            await processing_msg.edit(content=f'❌ Failed to process receipt: {error_msg}')
            
    except Exception as e:
        logger.error(f'Error processing receipt: {e}')
        await message.reply(f'❌ Error: {str(e)}')


@bot.tree.command(name='login', description='Login to your receipt account')
@app_commands.describe(
    email='Your email address',
    password='Your password'
)
async def login(interaction: discord.Interaction, email: str, password: str):
    """Login command"""
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        # Interaction expired, can't respond
        logger.warning('Interaction expired before deferring')
        return
    
    try:
        result = await api_client.login(email, password)
        
        if result['success']:
            user_id = str(interaction.user.id)
            user_sessions[user_id] = result['token']
            
            await interaction.followup.send(
                '✅ Login successful! You can now upload receipts.',
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f'❌ Login failed: {result.get("error", "Invalid credentials")}',
                ephemeral=True
            )
    except discord.errors.NotFound:
        logger.warning('Interaction expired, could not send response')
    except Exception as e:
        logger.error(f'Login error: {e}')
        try:
            await interaction.followup.send(
                f'❌ Error during login: {str(e)}',
                ephemeral=True
            )
        except discord.errors.NotFound:
            logger.warning('Could not send error message, interaction expired')


@bot.tree.command(name='logout', description='Logout from your account')
async def logout(interaction: discord.Interaction):
    """Logout command"""
    user_id = str(interaction.user.id)
    
    if user_id in user_sessions:
        del user_sessions[user_id]
        await interaction.response.send_message('✅ Logged out successfully!', ephemeral=True)
    else:
        await interaction.response.send_message('❌ You are not logged in!', ephemeral=True)


@bot.tree.command(name='receipts', description='View your recent receipts')
@app_commands.describe(
    limit='Number of receipts to show (default: 5)'
)
async def list_receipts(interaction: discord.Interaction, limit: Optional[int] = 5):
    """List recent receipts"""
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    if user_id not in user_sessions:
        await interaction.followup.send('❌ Please login first using `/login` command!')
        return
    
    try:
        token = user_sessions[user_id]
        result = await api_client.get_receipts(token, page=1, page_size=limit)
        
        if result['success']:
            receipts = result['data']['receipts']
            
            if not receipts:
                await interaction.followup.send('📭 No receipts found.')
                return
            
            # Cache receipts for easy reference
            cache_receipts(user_id, receipts)
            
            embed = discord.Embed(
                title=f'📄 Your Recent Receipts (Top {len(receipts)})',
                description='Use the number (e.g., `/receipt 1`) for easy access',
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            for idx, receipt in enumerate(receipts, 1):
                vendor = receipt.get('vendor', 'Unknown')
                date = receipt.get('date', 'N/A')
                amount = f"{receipt.get('currency', 'USD')} {receipt.get('total_amount', '0.00')}"
                status = receipt.get('processing_status', 'unknown')
                
                field_value = f"**Date:** {date}\n**Amount:** {amount}\n**Status:** {status}"
                
                embed.add_field(
                    name=f"#{idx} - {vendor}",
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text=f'Total: {result["data"]["total"]} receipts | Use /receipt <number> to view details')
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f'❌ Error: {result.get("error", "Failed to fetch receipts")}')
            
    except Exception as e:
        logger.error(f'Error fetching receipts: {e}')
        await interaction.followup.send(f'❌ Error: {str(e)}')


@bot.tree.command(name='receipt', description='View details of a specific receipt')
@app_commands.describe(
    receipt_id='Receipt number (e.g., 1) or full ID'
)
async def get_receipt(interaction: discord.Interaction, receipt_id: str):
    """Get specific receipt details"""
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    if user_id not in user_sessions:
        await interaction.followup.send('❌ Please login first using `/login` command!')
        return
    
    try:
        token = user_sessions[user_id]
        
        # Resolve receipt ID (number or UUID)
        resolved_id = resolve_receipt_id(user_id, receipt_id)
        
        # Check if it's still a short number (not resolved)
        if resolved_id.isdigit() and len(resolved_id) <= 3:
            await interaction.followup.send(
                '❌ Receipt number not found in cache.\n'
                '💡 Please run `/receipts` first to load the numbered list!',
                ephemeral=True
            )
            return
        
        result = await api_client.get_receipt(resolved_id, token)
        
        if result['success']:
            receipt = result['data']
            
            embed = discord.Embed(
                title=f'🧾 Receipt Details',
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name='ID', value=f"`{receipt.get('id')}`", inline=False)
            embed.add_field(name='Vendor', value=receipt.get('vendor', 'Unknown'), inline=True)
            embed.add_field(name='Date', value=receipt.get('date', 'N/A'), inline=True)
            embed.add_field(
                name='Total Amount',
                value=f"{receipt.get('currency', 'USD')} {receipt.get('total_amount', '0.00')}",
                inline=True
            )
            
            if receipt.get('category'):
                embed.add_field(name='Category', value=receipt['category'], inline=True)
            
            if receipt.get('tax_amount'):
                embed.add_field(
                    name='Tax',
                    value=f"{receipt.get('currency', 'USD')} {receipt.get('tax_amount')}",
                    inline=True
                )
            
            if receipt.get('payment_method'):
                embed.add_field(name='Payment Method', value=receipt['payment_method'], inline=True)
            
            embed.add_field(
                name='Status',
                value=receipt.get('processing_status', 'unknown'),
                inline=True
            )
            
            if receipt.get('notes'):
                embed.add_field(name='Notes', value=receipt['notes'], inline=False)
            
            embed.set_footer(text=f'Created: {receipt.get("created_at", "N/A")}')
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f'❌ Error: {result.get("error", "Receipt not found")}')
            
    except Exception as e:
        logger.error(f'Error fetching receipt: {e}')
        await interaction.followup.send(f'❌ Error: {str(e)}')


@bot.tree.command(name='search', description='Search receipts by vendor or category')
@app_commands.describe(
    vendor='Vendor name to search',
    category='Category to filter'
)
async def search_receipts(
    interaction: discord.Interaction,
    vendor: Optional[str] = None,
    category: Optional[str] = None
):
    """Search receipts"""
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    if user_id not in user_sessions:
        await interaction.followup.send('❌ Please login first using `/login` command!')
        return
    
    if not vendor and not category:
        await interaction.followup.send('❌ Please provide at least vendor or category to search!')
        return
    
    try:
        token = user_sessions[user_id]
        result = await api_client.search_receipts(token, vendor=vendor, category=category)
        
        if result['success']:
            receipts = result['data']['receipts']
            
            if not receipts:
                await interaction.followup.send('📭 No receipts found matching your criteria.')
                return
            
            embed = discord.Embed(
                title=f'🔍 Search Results',
                description=f'Found {len(receipts)} receipt(s)',
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            
            for receipt in receipts[:10]:  # Limit to 10 results
                vendor_name = receipt.get('vendor', 'Unknown')
                date = receipt.get('date', 'N/A')
                amount = f"{receipt.get('currency', 'USD')} {receipt.get('total_amount', '0.00')}"
                
                field_value = f"**Date:** {date}\n**Amount:** {amount}"
                
                embed.add_field(
                    name=vendor_name,
                    value=field_value,
                    inline=True
                )
            
            if len(receipts) > 10:
                embed.set_footer(text=f'Showing 10 of {len(receipts)} results')
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f'❌ Error: {result.get("error", "Search failed")}')
            
    except Exception as e:
        logger.error(f'Error searching receipts: {e}')
        await interaction.followup.send(f'❌ Error: {str(e)}')


@bot.tree.command(name='summary', description='Get your expense summary')
@app_commands.describe(
    period='Time period (week, month, year)',
)
async def get_summary(interaction: discord.Interaction, period: str = 'month'):
    """Get expense summary"""
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    if user_id not in user_sessions:
        await interaction.followup.send('❌ Please login first using `/login` command!')
        return
    
    try:
        token = user_sessions[user_id]
        
        # Get receipts and calculate summary
        result = await api_client.get_receipts(token, page=1, page_size=100)
        
        if result['success']:
            receipts = result['data']['receipts']
            
            # Filter by period
            now = datetime.now()
            if period == 'week':
                start_date = now - timedelta(days=7)
                title = 'Weekly Expense Summary'
            elif period == 'month':
                start_date = now - timedelta(days=30)
                title = 'Monthly Expense Summary'
            elif period == 'year':
                start_date = now - timedelta(days=365)
                title = 'Yearly Expense Summary'
            else:
                await interaction.followup.send('❌ Invalid period! Use: week, month, or year')
                return
            
            # Calculate totals
            total_amount = 0
            total_tax = 0
            count = 0
            categories = {}
            
            for receipt in receipts:
                receipt_date = datetime.fromisoformat(receipt['created_at'].replace('Z', '+00:00'))
                if receipt_date >= start_date:
                    count += 1
                    total_amount += float(receipt.get('total_amount', 0))
                    total_tax += float(receipt.get('tax_amount', 0) or 0)
                    
                    category = receipt.get('category', 'Uncategorized')
                    categories[category] = categories.get(category, 0) + float(receipt.get('total_amount', 0))
            
            embed = discord.Embed(
                title=f'📊 {title}',
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name='Total Receipts', value=str(count), inline=True)
            embed.add_field(name='Total Amount', value=f'USD {total_amount:.2f}', inline=True)
            embed.add_field(name='Total Tax', value=f'USD {total_tax:.2f}', inline=True)
            
            if categories:
                category_text = '\n'.join([f'**{cat}:** USD {amt:.2f}' for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]])
                embed.add_field(name='Top Categories', value=category_text, inline=False)
            
            embed.set_footer(text=f'Period: Last {period}')
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f'❌ Error: {result.get("error", "Failed to generate summary")}')
            
    except Exception as e:
        logger.error(f'Error generating summary: {e}')
        await interaction.followup.send(f'❌ Error: {str(e)}')


@tasks.loop(hours=24)
async def weekly_report():
    """Send weekly expense report to all logged-in users"""
    # Check if it's the scheduled day
    schedule_day = os.getenv('REPORT_SCHEDULE_DAY', 'monday').lower()
    current_day = datetime.now().strftime('%A').lower()
    
    if current_day != schedule_day:
        return
    
    logger.info('Sending weekly reports...')
    
    for user_id, token in user_sessions.items():
        try:
            user = await bot.fetch_user(int(user_id))
            if user:
                # Generate weekly summary
                result = await api_client.get_receipts(token, page=1, page_size=100)
                
                if result['success']:
                    receipts = result['data']['receipts']
                    
                    # Filter last week
                    week_ago = datetime.now() - timedelta(days=7)
                    weekly_receipts = [
                        r for r in receipts
                        if datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')) >= week_ago
                    ]
                    
                    if weekly_receipts:
                        total = sum(float(r.get('total_amount', 0)) for r in weekly_receipts)
                        
                        embed = discord.Embed(
                            title='📅 Weekly Expense Report',
                            description=f'Summary of your expenses for the past week',
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        
                        embed.add_field(name='Total Receipts', value=str(len(weekly_receipts)), inline=True)
                        embed.add_field(name='Total Spent', value=f'USD {total:.2f}', inline=True)
                        
                        await user.send(embed=embed)
                        logger.info(f'Sent weekly report to user {user_id}')
        except Exception as e:
            logger.error(f'Error sending weekly report to user {user_id}: {e}')


@bot.tree.command(name='delete', description='Delete a receipt by ID')
@app_commands.describe(receipt_id='Receipt number (e.g., 1) or full ID')
async def delete_receipt(interaction: discord.Interaction, receipt_id: str):
    """Delete a receipt"""
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        logger.warning('Interaction expired before deferring')
        return
    
    try:
        user_id = str(interaction.user.id)
        
        # Check if user is logged in
        if user_id not in user_sessions:
            await interaction.followup.send(
                '❌ Please login first using `/login`',
                ephemeral=True
            )
            return
        
        token = user_sessions[user_id]
        
        # Resolve receipt ID (number or UUID)
        resolved_id = resolve_receipt_id(user_id, receipt_id)
        
        # Check if it's still a short number (not resolved)
        if resolved_id.isdigit() and len(resolved_id) <= 3:
            await interaction.followup.send(
                '❌ Receipt number not found in cache.\n'
                '💡 Please run `/receipts` first to load the numbered list!',
                ephemeral=True
            )
            return
        
        # Delete receipt via API
        result = await api_client.delete_receipt(resolved_id, token)
        
        if result['success']:
            embed = discord.Embed(
                title='✅ Receipt Deleted',
                description=f'Receipt `{receipt_id}` has been deleted successfully.',
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                f'❌ Failed to delete receipt: {result.get("error", "Unknown error")}',
                ephemeral=True
            )
    except discord.errors.NotFound:
        logger.warning('Could not send response, interaction expired')
    except Exception as e:
        logger.error(f'Delete receipt error: {e}')
        try:
            await interaction.followup.send(
                f'❌ Error: {str(e)}',
                ephemeral=True
            )
        except discord.errors.NotFound:
            logger.warning('Could not send error message, interaction expired')


@bot.tree.command(name='help', description='Show available commands')
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title='🤖 Receipt Bot Help',
        description='Here are all available commands:',
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name='/login',
        value='Login to your account to start uploading receipts',
        inline=False
    )
    
    embed.add_field(
        name='/logout',
        value='Logout from your account',
        inline=False
    )
    
    embed.add_field(
        name='Send Image',
        value='Simply send any receipt image and I\'ll process it automatically!',
        inline=False
    )
    
    embed.add_field(
        name='/receipts [limit]',
        value='View your recent receipts (default: 5)',
        inline=False
    )
    
    embed.add_field(
        name='/receipt <id>',
        value='View details of a specific receipt',
        inline=False
    )
    
    embed.add_field(
        name='/search [vendor] [category]',
        value='Search receipts by vendor or category',
        inline=False
    )
    
    embed.add_field(
        name='/summary <period>',
        value='Get expense summary (week, month, year)',
        inline=False
    )
    
    embed.add_field(
        name='/delete <receipt_id>',
        value='Delete a receipt by its ID',
        inline=False
    )
    
    embed.set_footer(text='Receipt Processing Bot | Made with ❤️')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


def main():
    """Main function to run the bot"""
    if not TOKEN:
        logger.error('DISCORD_BOT_TOKEN not found in environment variables!')
        return
    
    logger.info('Starting Discord bot...')
    bot.run(TOKEN)


if __name__ == '__main__':
    main()
