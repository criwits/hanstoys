import os
import numpy as np
import matplotlib.pyplot as plt
import cv2
import argparse

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='fftbwm: FFT Blind Watermarking')
    parser.add_argument('image', help='image file')
    parser.add_argument('output', help='output file')
    parser.add_argument("-w", "--watermark", help="watermark file", required=False)
    parser.add_argument("-d", "--decode", help="decode watermark", action="store_true")
    parser.add_argument("-r", "--ratio", help="resizing ratio", type=float, default=3)
    parser.add_argument("-s", "--strength", help="watermark strength", type=float, default=0.005)
    parser.add_argument("-c", "--channel", help="channel", type=str, default="Cb")
    parser.add_argument("-n", "--sample", help="number of sampled center points", type=int, default=100)
    args = parser.parse_args()

    if args.channel not in ["Y", "Cb", "Cr"]:
        print("Invalid channel. Choose from Y, Cb, Cr")
        exit(1)

    # Load image
    image_path = os.path.join(args.image)
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    img_ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    img_y, img_cr, img_cb = cv2.split(img_ycrcb)
    img_working_channel = img_cb if args.channel == "Cb" else img_cr if args.channel == "Cr" else img_y

    fft = np.fft.fft2(img_working_channel)
    fft_shift = np.fft.fftshift(fft)

    if args.decode:
        plt.figure(figsize=(10, 10))
        plt.imshow(np.log(1+np.abs(fft_shift)), cmap='gray')
        plt.axis('off')
        plt.colorbar()
        plt.title(f"FFT of {args.channel} channel")
        plt.savefig(args.output)
        exit(0)
    else:
        if args.watermark is None:
            print("Watermark file is required")
            exit(1)
        watermark_path = os.path.join(args.watermark)
        wm_img = cv2.imread(watermark_path, cv2.IMREAD_GRAYSCALE)
        _, wm_img_bw = cv2.threshold(wm_img, 127, 255, cv2.THRESH_BINARY)

        # sample some center points
        rows, cols = fft_shift.shape
        center_points = []
        for i in range(args.sample):
            center_points.append((np.random.randint(rows//2-10, rows//2+10), np.random.randint(cols//2-10, cols//2+10)))

        # get average amplitude of center points
        amplitudes = []
        for r, c in center_points:
            amplitudes.append(np.abs(fft_shift[r, c]))
        avg_amplitude = np.mean(amplitudes)

        resize_ratio = args.ratio
        image_aspect_ratio = cols / rows
        wm_aspect_ratio = wm_img_bw.shape[1] / wm_img_bw.shape[0]
        if wm_aspect_ratio > image_aspect_ratio:
            # wm is wider, resize width
            new_cols = cols / resize_ratio
            new_rows = new_cols / wm_aspect_ratio
        else:
            # wm is taller, resize height
            new_rows = rows / resize_ratio
            new_cols = new_rows * wm_aspect_ratio


        wm_img_resized = cv2.resize(wm_img_bw, (int(new_cols), int(new_rows)), interpolation=cv2.INTER_AREA)
        wm_img_resized = np.where(wm_img_resized > 127, 0, 1)

        strength = args.strength
        wm_height, wm_width = wm_img_resized.shape

        for i in range(wm_height):
            for j in range(wm_width):
                if wm_img_resized[i, j] == 1:
                    # Left top
                    original_amp = np.abs(fft_shift[i, j])
                    scale = avg_amplitude / original_amp
                    fft_shift[i, j] = fft_shift[i, j] * scale * strength
                    # Right top
                    original_amp = np.abs(fft_shift[i, cols-wm_width+j])
                    scale = avg_amplitude / original_amp
                    fft_shift[i, cols-wm_width+j] = fft_shift[i, cols-wm_width+j] * scale * strength

        new_fft = np.fft.ifftshift(fft_shift)
        new_fft = np.fft.ifft2(new_fft)
        new_fft = np.abs(new_fft)
        new_fft = np.clip(new_fft, 0, 255).astype(np.uint8)

        if args.channel == "Cb":
            img_cb = new_fft
        elif args.channel == "Cr":
            img_cr = new_fft
        else:
            img_y = new_fft

        new_img_ycrcb = cv2.merge([img_y, img_cr, img_cb])
        new_img = cv2.cvtColor(new_img_ycrcb, cv2.COLOR_YCrCb2BGR)
        cv2.imwrite(args.output, new_img)
        exit(0)
