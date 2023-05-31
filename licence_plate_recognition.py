import cv2
import imutils
import numpy as np
import pytesseract
import time
import requests
from bs4 import BeautifulSoup
import tkinter as Tk
# path to tesseract.exe OCR 
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tessreact-OCR\tesseract.exe'

# Initialize webcam to record(change number to switch camera input device)
cap = cv2.VideoCapture(0)

# Initialize timer and plate number variables
last_print_time = time.time()
detected_plate = None
scraping_completed = False
ul = None  
gtm_merinfo_a = None

while not scraping_completed:
    # Read frame from webcam
    ret, frame = cap.read()

    # Resize frame
    frame = cv2.resize(frame, (600, 400))

    # Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 13, 15, 15)
    # look for edges on the gray frame
    edged = cv2.Canny(gray, 30, 200)
    # Find contours in the edge frame
    contours = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # Extract the actual contours from the result
    contours = imutils.grab_contours(contours)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    # Initialize the variable to store the final contour
    license_plate_contour = None

    for c in contours:
        # Calculate the perimeter of the contour
        perimeter  = cv2.arcLength(c, True)
        # Approximate the contour shape
        approx = cv2.approxPolyDP(c, 0.018 * perimeter, True)
        # chack if there is 4 corners
        if len(approx) == 4:
            license_plate_contour = approx
            break

    if license_plate_contour  is None:
        detected_plate = None
        print("No contour detected")
    else:
        # crate a zoomed in image of the plate
        mask = np.zeros(gray.shape, np.uint8)
        new_image = cv2.drawContours(mask, [license_plate_contour ], 0, 255, -1)
        new_image = cv2.bitwise_and(frame, frame, mask=mask)

        # Find the indices where the mask is white (255)
        (x, y) = np.where(mask == 255)
        # Determine the top-left and bottom-right coordinates of the bounding rectangle around the license plate
        (topx, topy) = (np.min(x), np.min(y))
        (bottomx, bottomy) = (np.max(x), np.max(y))
        # Crop the grayscale image using the bounding rectangle coordinates
        Cropped = gray[topx:bottomx + 1, topy:bottomy + 1]

        # apply OCR to extract plate number using the 7th parameter model for the OCR(Apparantly best for reading plates,signs ETC)
        plate_number = pytesseract.image_to_string(Cropped, config='--psm 7')

        if detected_plate != plate_number:
            current_time = time.time()
            elapsed_time = current_time - last_print_time
            if elapsed_time >= 10:
                detected_plate = plate_number
                print("Detected license plate Number is:", plate_number)

                # code to webscarper to get information about teh plate from biluppgifter.se
                url = f"https://biluppgifter.se/fordon/{plate_number}"

                try:
                    response = requests.get(url)
                    soup = BeautifulSoup(response.content, "html.parser")
                    #look for the "list-data enlarge" element on the site
                    ul = soup.find("ul", class_="list-data enlarge")

                    if ul:
                        # Extract the desired data from the ul
                        print("Deatails about", plate_number)
                        lis = ul.find_all("li")
                        results = ""
                        for li in lis[:5]:
                            # displaying the first 5 elements
                            print(li.get_text().strip())
                            results += li.get_text().strip() + "\n"
                    else:
                        print("No data found for the specified license plate.")

                    try:
                        response = requests.get(url)
                        soup = BeautifulSoup(response.content, "html.parser")

                        gtm_merinfo_a = soup.find("a", class_="gtm-merinfo")

                        if gtm_merinfo_a:
                            # Extract the link from the "gtm-merinfo" a tag
                            merinfo_url = gtm_merinfo_a["href"]

                            # Scrape data from the linked page
                            merinfo_response = requests.get(merinfo_url)
                            merinfo_soup = BeautifulSoup(merinfo_response.content, "html.parser")

                            # Extract data from the linked page
                            span_element = merinfo_soup.find("span", class_="namn mb-2")
                            if span_element:
                                owner = span_element.get_text().strip()
                                print("Owner of the car is: ", owner)
                            else:
                                print("No owner found")
                        else:
                            print("No 'gtm-merinfo' link found for the specified license plate.")

                    except requests.exceptions.RequestException as e:
                        print("Error:", e)

                except requests.exceptions.RequestException as e:
                    print("Error:", e)
                last_print_time = current_time

        frame = cv2.resize(frame, (500, 300))
        Cropped = cv2.resize(Cropped, (400, 200))

        cv2.imshow('car', frame)
        cv2.imshow('Cropped', Cropped)

    # Check if all information has been printed
    if ul and gtm_merinfo_a:
        scraping_completed = True

    # Exit if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close windows
cap.release()
cv2.destroyAllWindows()

# print the scraped information in a window using tkinter
label = Tk.Label(None, text= owner + "\n" + results, font=('Times', '18'),fg='black', width=50, height=15)
label.pack()
label.mainloop()