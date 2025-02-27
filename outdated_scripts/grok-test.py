from grok_client import GrokClient

# Your cookie values
cookies = {
    "x-anonuserid": "b4507c57-a948-482e-8136-780c5c84a0b1",
    "x-challenge": "DihL68ZFtBXalCC%2BULwZ%2BmrOQUb7AsS9zTGaDRAv3JpysrX3QnBbllKCCP741TacDN09kDe61LdxQSKeTQahXPTMCuCnRCXE6hB62DzHaaN4yXRiYNeo4jwHqpux7Qzj4i93uDtacIOXO8BUFeI2ATSGFqhmrJM%2Bm8O5uYkhDY%2BwM%2Bq%2Fnbc%3D",
    "x-signature": "Pn6TTqRTbqXG62zgbNvdS96GPeeZZU%2Fbi98NTNif5IISJVrtdmkirXD%2FugJntQ13YPori3lrt8TOPiB7fKEitQ%3D%3D",
    "sso": "eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMjRmZDc5YzQtZGFjNi00MGI0LWFjZGMtNzJiMGNhMWFlNGE4In0.oitDPbuVQHr8dfcH7zW-VFRLPMMlafpMxLpx1G49Xes",
    "sso-rw": "eyJhbGciOiJIUzI1NiJ9.eyJzZXNzaW9uX2lkIjoiMjRmZDc5YzQtZGFjNi00MGI0LWFjZGMtNzJiMGNhMWFlNGE4In0.oitDPbuVQHr8dfcH7zW-VFRLPMMlafpMxLpx1G49Xes"
}

# Initialize the client
client = GrokClient(cookies)

# Send a message and get response
response = client.send_message("write a poem")
print(response)