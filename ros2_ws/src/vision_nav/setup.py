from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'vision_nav'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Mohtasim Hadi Rafi',
    maintainer_email='mohtasimhadi@gmail.com',
    description='Vision-based crop row navigation',
    license='MIT',
    entry_points={
        'console_scripts': [
            'camera_viewer          = vision_nav.camera_viewer:main',
            'row_detector           = vision_nav.row_detector:main',
            'vanishing_point        = vision_nav.vanishing_point:main',
            'vision_pipeline        = vision_nav.vision_pipeline:main',
            'visual_servo           = vision_nav.visual_servo:main',
            'field_traverser        = vision_nav.field_traverser:main',
        ],
    },
)
