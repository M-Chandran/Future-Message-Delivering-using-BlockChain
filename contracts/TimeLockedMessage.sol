// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FutureMessageChain {
    enum MessageType { Text, Image, Document }

    struct Message {
        uint256 messageId;
        address sender;
        address receiver;
        string ipfsHash;
        MessageType messageType;
        uint256 unlockTime;
        uint256 createdTime;
        bool isRevealed;
        bool isDeleted;
    }

    mapping(uint256 => Message) public messages;
    mapping(address => uint256[]) public userMessages;
    uint256 public messageCount;

    event MessageCreated(uint256 indexed messageId, address indexed sender, address indexed receiver, MessageType messageType, uint256 unlockTime);
    event MessageRevealed(uint256 indexed messageId, address indexed receiver);
    event MessageDeleted(uint256 indexed messageId, address indexed sender);

    modifier onlyReceiver(uint256 _messageId) {
        require(messages[_messageId].receiver == msg.sender, "Not the receiver");
        _;
    }

    modifier onlySender(uint256 _messageId) {
        require(messages[_messageId].sender == msg.sender, "Not the sender");
        _;
    }

    modifier messageExists(uint256 _messageId) {
        require(_messageId > 0 && _messageId <= messageCount, "Message does not exist");
        _;
    }

    modifier notDeleted(uint256 _messageId) {
        require(!messages[_messageId].isDeleted, "Message is deleted");
        _;
    }

    function createMessage(
        address _receiver,
        string memory _ipfsHash,
        MessageType _messageType,
        uint256 _unlockTime
    ) external returns (uint256) {
        require(_receiver != address(0), "Invalid receiver address");
        require(_unlockTime > block.timestamp, "Unlock time must be in the future");
        require(bytes(_ipfsHash).length > 0, "IPFS hash cannot be empty");

        messageCount++;
        messages[messageCount] = Message({
            messageId: messageCount,
            sender: msg.sender,
            receiver: _receiver,
            ipfsHash: _ipfsHash,
            messageType: _messageType,
            unlockTime: _unlockTime,
            createdTime: block.timestamp,
            isRevealed: false,
            isDeleted: false
        });

        userMessages[_receiver].push(messageCount);

        emit MessageCreated(messageCount, msg.sender, _receiver, _messageType, _unlockTime);
        return messageCount;
    }

    function getMyMessages() external view returns (Message[] memory) {
        uint256[] memory messageIds = userMessages[msg.sender];
        Message[] memory userMsgs = new Message[](messageIds.length);

        for (uint256 i = 0; i < messageIds.length; i++) {
            userMsgs[i] = messages[messageIds[i]];
        }

        return userMsgs;
    }

    function revealMessage(uint256 _messageId)
        external
        onlyReceiver(_messageId)
        messageExists(_messageId)
        notDeleted(_messageId)
    {
        require(block.timestamp >= messages[_messageId].unlockTime, "Message is still locked");
        require(!messages[_messageId].isRevealed, "Message already revealed");

        messages[_messageId].isRevealed = true;
        emit MessageRevealed(_messageId, msg.sender);
    }

    function deleteMessage(uint256 _messageId)
        external
        onlySender(_messageId)
        messageExists(_messageId)
        notDeleted(_messageId)
    {
        messages[_messageId].isDeleted = true;
        emit MessageDeleted(_messageId, msg.sender);
    }

    function getMessageInfo(uint256 _messageId)
        external
        view
        messageExists(_messageId)
        notDeleted(_messageId)
        returns (
            address sender,
            address receiver,
            string memory ipfsHash,
            MessageType messageType,
            uint256 unlockTime,
            uint256 createdTime,
            bool isRevealed
        )
    {
        Message memory msg = messages[_messageId];
        return (
            msg.sender,
            msg.receiver,
            msg.ipfsHash,
            msg.messageType,
            msg.unlockTime,
            msg.createdTime,
            msg.isRevealed
        );
    }

    function getBlockTimestamp() external view returns (uint256) {
        return block.timestamp;
    }

    function canReveal(uint256 _messageId) external view returns (bool) {
        if (_messageId == 0 || _messageId > messageCount) return false;
        Message memory msg = messages[_messageId];
        return !msg.isDeleted &&
               msg.receiver == msg.sender &&
               block.timestamp >= msg.unlockTime &&
               !msg.isRevealed;
    }
}
