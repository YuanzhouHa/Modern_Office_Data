import random
import re
import os
import unreal
from datetime import datetime
from typing import Optional, Callable

def clean_sequencer(level_sequence):
    bindings = level_sequence.get_bindings()
    for b in bindings:
        # b_display_name = str(b.get_display_name())
        # if "Camera" not in  b_display_name:
        #     b.remove()
        b.remove()
   
def select_random_asset(assets_path, asset_class=None, predicate:Optional[Callable]=None):
    eal = unreal.EditorAssetLibrary()
    assets = eal.list_assets(assets_path)

    if asset_class is not None:
        filtered_assets = []
        for asset in assets:
            try:
                asset_name = os.path.splitext(asset)[0]
                if eal.find_asset_data(asset_name).asset_class_path.asset_name == asset_class:
                    filtered_assets.append(asset)
            except:
                continue

        assets = filtered_assets

    if predicate is not None:
        filtered_assets = []
        for asset in assets:
            if predicate(asset):
                filtered_assets.append(asset)

        assets = filtered_assets

    selected_asset_path = random.choice(assets)

    return selected_asset_path

def spawn_actor(asset_path, location=unreal.Vector(0.0, 0.0, 0.0)):
    # spawn actor into level
    obj = unreal.load_asset(asset_path)
    rotation = unreal.Rotator(0, 0, 0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(object_to_use=obj,
                                                              location=location,
                                                              rotation=rotation)

    actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    # actor.get_editor_property('render_component').set_editor_property('cast_shadow', self.add_sprite_based_shadow)

    return actor

def add_animation_to_actor(spawnable_actor, animation_path):
    # Get the skeleton animation track class
    anim_track = spawnable_actor.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    # Add a new animation section
    animation_section = anim_track.add_section()
    # Set the skeletal animation asset
    animation_asset = unreal.load_asset(animation_path)
    animation_section.params.animation = animation_asset

    # Set the Section Range
    frame_rate = 30  # level_sequence.get_frame_rate()
    start_frame = 0
    end_frame = animation_asset.get_editor_property('sequence_length') * frame_rate.numerator / frame_rate.denominator
    animation_section.set_range(start_frame, end_frame)

def find_relevant_assets(level_sequence):

    camera_re = re.compile("SuperCineCameraActor_([0-9]+)")
    target_point_re = re.compile("TargetPoint_([0-9]+)")

    cameras = {}
    target_points = {}
    skylight =  None
    # hdri_backdrop = None
    #all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    # ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    # current_world = ues.get_editor_world()
    # bound_objects = unreal.SequencerTools().get_bound_objects(current_world, level_sequence, level_sequence.get_bindings(), level_sequence.get_playback_range())
    # for b_obj in bound_objects:
    #     for actor1 in b_obj.bound_objects:
    #         print(actor1.get_name())
    #         if 'CineCamera' in actor1.get_name():
    #             camera = actor1
    #             break
    all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in all_actors:
        label = actor.get_actor_label()
        name  = actor.get_name()
        # if 'HDRIBackdrop' in actor.get_name():
        #     hdri_backdrop = actor
        camera_matches = camera_re.search(label)
        target_point_matches = target_point_re.search(label)

        if camera_matches is not None:
            cameras[camera_matches.group(1)] = actor
        if target_point_matches is not None:
            target_points[target_point_matches.group(1)] = actor
        if 'SkyLight' in name:
            skylight = actor


    # return camera, hdri_backdrop
    return cameras, target_points, skylight

def random_hdri(hdri_backdrop):
    selected_hdri_path = select_random_asset('/HDRIBackdrop/Textures')
    hdri_texture = unreal.load_asset(selected_hdri_path)
    hdri_backdrop.set_editor_property('cubemap', hdri_texture)

def random_cubemap(skylight):
    cubemap_path = select_random_asset('/Game/HDRI/', asset_class='TextureCube')
    cubemap_asset = unreal.load_asset(cubemap_path)

    if cubemap_asset is not None:
        # Access the skylight component
        skylight_comp = skylight.get_editor_property('light_component')
        # Assign the new cubemap
        skylight_comp.set_editor_property('cubemap', cubemap_asset)
        
        # Update the skylight to apply the new cubemap
        skylight_comp.recapture_sky() 

def bind_camera_to_level_sequence(level_sequence, camera, character_location, start_frame=0, num_frames=0, move_radius=500):
    # Get the Camera Cuts track manually
    camera_cuts_track = None
    for track in level_sequence.get_master_tracks():
        if track.get_class() == unreal.MovieSceneCameraCutTrack.static_class():
            camera_cuts_track = track
            break

    if camera_cuts_track is None:
        print("No Camera Cuts track found.")
        return

    # Find the section (usually only one for camera cuts)
    sections = camera_cuts_track.get_sections()

    for section in sections:
        if isinstance(section, unreal.MovieSceneCameraCutSection):
            # Replace the camera binding 
            camera_binding = level_sequence.add_possessable(camera)
            camera_binding_id = level_sequence.get_binding_id(camera_binding)

            # Set the new camera binding to the camera cut section
            section.set_camera_binding_id(camera_binding_id)
            print("Camera cut updated to use:", camera.get_name())

    # Add Transform Track
    transform_track = camera_binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section = transform_track.add_section()
    transform_section.set_range(start_frame, start_frame + num_frames)

    # Get transform channels
    channels = transform_section.get_all_channels()
    loc_x_channel = channels[0]
    loc_y_channel = channels[1]
    loc_z_channel = channels[2]

    # Get original camera location as center point
    #center_location = camera.get_actor_location()
    center_location = character_location +  unreal.Vector(0.0, 0.0, 100.0)  # Offset to avoid ground collision
    # Generate random keyframes
    # frames = sorted(random.sample(range(start_frame+1, start_frame+num_frames-1), num_keyframes-2))
    frames = [start_frame, start_frame+num_frames]

    # Add keyframes
    for frame in frames:
        # Randomize location around the center within a radius
        random_location = center_location + unreal.Vector(
            random.uniform(-move_radius, move_radius),
            random.uniform(-move_radius, move_radius),
            random.uniform(-move_radius/2, move_radius/2)
        )

        frame_number = unreal.FrameNumber(frame)

        # Add location keys
        loc_x_channel.add_key(frame_number, random_location.x)
        loc_y_channel.add_key(frame_number, random_location.y)
        loc_z_channel.add_key(frame_number, random_location.z)
        
def add_actor_to_layer(actor, layer_name="character"):
    layer_subsystem = unreal.get_editor_subsystem(unreal.LayersSubsystem)
    # Add the actor to the specified layer， if it doesn't exist, add_actor_to_layer will create it
    layer_subsystem.add_actor_to_layer(actor, layer_name)

RENDER_TIMES = 3
current_round = 0  # 全局计数
 # 全局唯一时间戳，防止路径冲突

def render_one_round():
    global current_round
    current_round += 1
    unreal.log(f"========== Start Render Round {current_round}/{RENDER_TIMES} ==========")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") 
    output_path = f"D:\\SyntheticData\\MordenOffice\\RandomCamera\\{timestamp}\\"
    
    level_sequence = unreal.EditorAssetLibrary.load_asset('/Game/RenderSequencer.RenderSequencer')
    clean_sequencer(level_sequence)

    cameras, target_points, skylight = find_relevant_assets(level_sequence)
    random_keys = [k for k in cameras.keys() if k in target_points.keys()]
    random_key = random.choice(random_keys)
    camera = cameras[random_key]
    target_point = target_points[random_key]
    random_cubemap(skylight)

    location = target_point.get_actor_location()

    selected_skeletal_mesh_path = select_random_asset('/Game/ActorcoreCharacterBaked', asset_class='SkeletalMesh')
    a_pose_animation_name = os.path.splitext(selected_skeletal_mesh_path)[-1] + "_Anim"
    def not_a_pose_animation(asset:str):
        return not asset.endswith(a_pose_animation_name)
    baked_animation_directory_path = os.path.dirname(selected_skeletal_mesh_path)
    selected_animation_path = select_random_asset(baked_animation_directory_path, asset_class="AnimSequence", predicate=not_a_pose_animation)

    print(f"[{current_round}/{RENDER_TIMES}] Skeletal Mesh: {selected_skeletal_mesh_path}")
    print(f"[{current_round}/{RENDER_TIMES}] Animation: {selected_animation_path}")

    actor = spawn_actor(asset_path=selected_skeletal_mesh_path, location=location)
    add_actor_to_layer(actor, layer_name="character")
    spawnable_actor = level_sequence.add_spawnable_from_instance(actor)
    add_animation_to_actor(spawnable_actor, animation_path=selected_animation_path)

    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(actor)
    bind_camera_to_level_sequence(level_sequence, camera, location, start_frame=0, num_frames=300, move_radius=800)
    unreal.log(f"[{current_round}/{RENDER_TIMES}] Selected character and animation: {selected_skeletal_mesh_path}, {selected_animation_path}")

            
    # 关键：把“继续下一轮”动作绑定到movie_finished回调里
    render_with_callback(output_path=output_path, mode="rgb")

# 这里改写你的render函数，让它支持外部回调
def render_with_callback(output_path, start_frame=0, num_frames=0, mode="rgb"):
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    pipelineQueue = subsystem.get_queue()
    for job in pipelineQueue.get_jobs():
        pipelineQueue.delete_job(job)

    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = ues.get_editor_world()
    map_name = current_world.get_path_name()

    job = pipelineQueue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.set_editor_property('map', unreal.SoftObjectPath(map_name))
    job.set_editor_property('sequence', unreal.SoftObjectPath('/Game/RenderSequencer'))
    job.author = "Voia"
    job.job_name = "Synthetic Data"

    if mode == 'rgb':
        newConfig = unreal.load_asset("/Game/MoviePipelinePrimaryConfig/RGB")
    elif mode == 'normals':
        newConfig = unreal.load_asset("/Game/MoviePipelinePrimaryConfig/CameraNormal")
    else:
        newConfig = unreal.load_asset("/Game/MoviePipelinePrimaryConfig/Alpha_Mask")
    job.set_configuration(newConfig)

    outputSetting = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    outputSetting.output_resolution = unreal.IntPoint(1920, 1080)
    outputSetting.file_name_format = "Image.{render_pass}.{frame_number}"
    outputSetting.flush_disk_writes_per_shot = True
    outputSetting.output_directory = unreal.DirectoryPath(path=f'{output_path}/{mode}')
    use_custom_playback_range = num_frames > 0
    outputSetting.use_custom_playback_range = use_custom_playback_range
    outputSetting.custom_start_frame = start_frame
    outputSetting.custom_end_frame = start_frame + num_frames

    renderPass = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    jpg_settings = job.get_configuration().find_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
    job.get_configuration().remove_setting(jpg_settings)
    png_settings = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    # 可根据mode切换alpha写入
    if mode == 'rgb':
        png_settings.set_editor_property('write_alpha', False)
    else:
        png_settings.set_editor_property('write_alpha', True)
    job.get_configuration().initialize_transient_settings()

    error_callback = unreal.OnMoviePipelineExecutorErrored()
    def movie_error(pipeline_executor, pipeline_with_error, is_fatal, error_text):
        unreal.log(pipeline_executor)
        unreal.log(pipeline_with_error)
        unreal.log(is_fatal)
        unreal.log(error_text)
    error_callback.add_callable(movie_error)

    # 关键：movie_finished回调自动继续渲染下一模式/下一轮
    def movie_finished(pipeline_executor, success):
        unreal.log('movie finished')
        unreal.log(pipeline_executor)
        unreal.log(success)
        if mode == 'rgb':
            # 渲染Normal
            render_with_callback(output_path=output_path, mode="normals")
        elif mode == 'normals':
            # 渲染Alpha
            render_with_callback(output_path=output_path, mode="rgb_alpha")
        elif mode == 'rgb_alpha':
            global current_round
            if current_round < RENDER_TIMES:
                # 自动进入下一轮
                render_one_round()
            else:
                unreal.log("========== All renders completed. ==========")
                #unreal.SystemLibrary.quit_editor()

    finished_callback = unreal.OnMoviePipelineExecutorFinished()
    finished_callback.add_callable(movie_finished)

    unreal.log("Starting Executor")
    global executor
    executor = unreal.MoviePipelinePIEExecutor(subsystem)
    executor.set_editor_property('on_executor_errored_delegate', error_callback)
    executor.set_editor_property('on_executor_finished_delegate', finished_callback)
    subsystem.render_queue_with_executor_instance(executor)

# 启动
if __name__ == '__main__':
    current_round = 0
    render_one_round()

