# Setup and Deployment Guide for Send Message to the Future

## Prerequisites

- Python 3.8 or higher
- Node.js and npm (for frontend development)
- Ganache (for local Ethereum blockchain)
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd send-message-to-the-future
```

### 2. Set Up Python Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Ganache

1. Install Ganache from https://trufflesuite.com/ganache/
2. Start Ganache and note the RPC server URL (usually http://127.0.0.1:7545)
3. Copy the first account's private key for deployment

### 5. Deploy Smart Contract

1. Install Truffle globally:
```bash
npm install -g truffle
```

2. Compile and deploy the contract:
```bash
cd contracts
truffle init
# Copy TimeLockedMessage.sol to contracts/ directory
truffle compile
truffle migrate --network development
```

3. Note the deployed contract address and update it in `backend/app.py`

### 6. Configure Environment Variables

Create a `.env` file in the backend directory:

```
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
WEB3_PROVIDER=http://127.0.0.1:7545
CONTRACT_ADDRESS=0x...
```

### 7. Initialize Database

The application uses CSV files for storage. They are automatically created when the app starts.

### 8. Run the Application

```bash
cd backend
python app.py
```

The application will be available at http://localhost:5000

## Deployment

### Using Docker

1. Build the Docker image:
```bash
docker build -t send-message-to-the-future .
```

2. Run the container:
```bash
docker run -p 5000:5000 send-message-to-the-future
```

### Cloud Deployment

For production deployment, consider using:
- AWS EC2 or Elastic Beanstalk
- Google Cloud App Engine
- Heroku
- DigitalOcean App Platform

Remember to:
- Set production environment variables
- Use a production-grade database instead of CSV files
- Configure HTTPS
- Set up proper logging and monitoring

## Testing

### Unit Tests

```bash
cd backend
python -m pytest
```

### Integration Tests

1. Start the application
2. Use tools like Postman to test API endpoints
3. Test blockchain interactions with Ganache

## Troubleshooting

### Common Issues

1. **Web3 Connection Error**: Ensure Ganache is running and the RPC URL is correct
2. **Contract Deployment Failed**: Check your private key and network configuration
3. **CSV Permission Error**: Ensure the storage directory has write permissions
4. **Port Already in Use**: Change the Flask port in app.py

### Logs

Check Flask logs for detailed error messages:
```bash
python app.py  # Logs will be displayed in the console
```

## Security Considerations

- Change the default SECRET_KEY in production
- Use environment variables for sensitive data
- Implement rate limiting for API endpoints
- Regularly update dependencies
- Use HTTPS in production
- Consider implementing additional authentication mechanisms

## Future Enhancements

- Replace CSV with a proper database (PostgreSQL/MySQL)
- Add email verification for user registration
- Implement mobile app using React Native
- Add AI-powered message analysis features
- Integrate with cloud storage for larger messages
