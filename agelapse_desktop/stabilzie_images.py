import os
from src.face_stabilizer import stabilize_image_directory


def stabilize_images_in_directory(input_dir: str, output_dir: str, framerate: int = 15) -> None:
    """
    Stabilize all images in the specified input directory and save them to the output directory.

    Args:
        input_dir (str): Path to the directory containing the input images.
        output_dir (str): Path to the directory where stabilized images will be saved.
        framerate (int, optional): Framerate for the output video. Defaults to 15.

    Raises:
        FileNotFoundError: If the input directory doesn't exist.
        NotADirectoryError: If the input path is not a directory.
    """
    # Validate input directory
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"The input directory '{
                                input_dir}' does not exist.")
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(
            f"The input path '{input_dir}' is not a directory.")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print(f"[LOG] Cleaning output directory: {output_dir} and {input_dir}")
    for file in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, file))

    print(f"[LOG] Starting image stabilization process...")
    print(f"[LOG] Input directory: {input_dir}")
    print(f"[LOG] Output directory: {output_dir}")

    # Call the existing stabilize_image_directory function
    stabilize_image_directory(input_dir, output_dir)

    print(f"[LOG] Image stabilization complete. Stabilized images saved to: {
          output_dir}")

    # Optionally, you can add video compilation here if needed
    # from src.video_compile import compile_video
    # output_video_path = os.path.join(output_dir, "stabilized_video.mp4")
    # compile_video(output_dir, output_video_path, framerate)
    # print(f"[LOG] Video compilation complete. Video saved to: {output_video_path}")


# Example usage:
stabilize_images_in_directory("/Users/tomer.rosenfeld/Desktop/timelapse/images/yuval_cropped",
                              "/Users/tomer.rosenfeld/AgeLapse/Stabilized_Images")
