# Order total service

The checkout release reads totals from this small service before displaying the
order summary. The local test covers the standard US order used by the browser
fixture; other countries and boundary prices are supported by the function
contract but are not represented in that one example.
